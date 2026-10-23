from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import get_db
import httpx

router = APIRouter(
    prefix="/api/chat",
    tags=["Similarity Search & Generation"]
)

OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:latest"
LLM_MODEL = "qwen2.5:7b"  # Change to "mistral" or whatever local model you have pulled

class QueryRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    question: str = Field(..., min_length=1)
    limit: int = Field(default=3, ge=1, le=10)

@router.post("/search", status_code=status.HTTP_200_OK)
async def semantic_search_and_chat(data: QueryRequest, db: Session = Depends(get_db)):
    safe_username = data.username.lower()
    table_name = f"tenant_{safe_username}"
    
    # 1. Verify Table Existence
    table_check = db.execute(
        text("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :table)"),
        {"table": table_name}
    ).scalar()
    
    if not table_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data store found for user '{data.username}'."
        )

    # 2. Vectorize Search Query via Ollama
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": data.question}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to vectorize search query via Ollama.")
                
            query_vector = response.json().get("embeddings", [])[0]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama embedding failure: {str(e)}")

    # 3. Query PostgreSQL for Context Chunks
    search_sql = f"""
    SELECT text_chunk 
    FROM {table_name}
    ORDER BY embedding <=> :vector
    LIMIT :limit;
    """
    
    try:
        result = db.execute(text(search_sql), {"vector": str(query_vector), "limit": data.limit})
        context_chunks = [row[0] for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database retrieval failed: {str(e)}")

    if not context_chunks:
        return {
            "answer": "I couldn't find any information in your documents to answer this question.",
            "sources": []
        }

    # 4. Synthesize the System Prompt and Context
    combined_context = "\n\n".join(context_chunks)
    system_prompt = (
        "You are a helpful AI assistant. Use the following pieces of retrieved context "
        "to answer the user's question accurately. If you don't know the answer, say that you don't know.\n\n"
        f"--- START RETRIEVED CONTEXT ---\n{combined_context}\n--- END RETRIEVED CONTEXT ---"
    )

    # 5. Generate Response via Ollama LLM
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            llm_response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": LLM_MODEL,
                    "prompt": f"{system_prompt}\n\nUser Question: {data.question}\nAnswer:",
                    "stream": False
                }
            )
            
            if llm_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama LLM generation failure.")
                
            generated_answer = llm_response.json().get("response", "").strip()

        return {
            "status": "success",
            "query": data.question,
            "answer": generated_answer,
            "retrieved_context_used": context_chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama generation failure: {str(e)}")
