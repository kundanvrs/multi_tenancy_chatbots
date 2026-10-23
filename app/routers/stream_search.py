from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import get_db
import httpx
import json

router = APIRouter(
    prefix="/api/chat",
    tags=["Similarity Search & Streaming Generation"]
)

OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:latest"
LLM_MODEL = "qwen2.5:7b"  # Ensure you ran `ollama pull qwen2.5:7b` to have this model available locally

class QueryRequest(BaseModel):
    # Fixed pattern to correctly allow alphanumeric strings ending natively without a literal "$"
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    question: str = Field(..., min_length=1)
    limit: int = Field(default=3, ge=1, le=10)

@router.post("/stream", status_code=status.HTTP_200_OK)
async def semantic_stream_chat(data: QueryRequest, db: Session = Depends(get_db)):
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
        # 2. Vectorize Search Query via Ollama
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if len(data.question) <10:
                data.question = f"{data.question} Please provide a detailed answer."
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": data.question}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to generate query embedding.")
            
            response_json = response.json()
            raw_embeddings = response_json.get("embeddings", [])
            
            # 🚨 FIX: Extract the inner flat list safely if it's nested [[...]]
            if raw_embeddings and isinstance(raw_embeddings, list):
                if isinstance(raw_embeddings[0], list):
                    query_vector = raw_embeddings[0]  # Extracts the clean flat array [x, y, z...]
                else:
                    query_vector = raw_embeddings
            else:
                raise HTTPException(status_code=500, detail="Ollama returned an empty embedding list.")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama embedding engine offline: {str(e)}")

    # 3. Query pgvector for matching chunks
    search_sql = f"""
    SELECT text_chunk FROM {table_name}
    ORDER BY embedding <=> :vector LIMIT :limit;
    """
    try:
        result = db.execute(text(search_sql), {"vector": str(query_vector), "limit": data.limit})
        context_chunks = [row[0] for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database retrieval failure: {str(e)}")

    # 4. Synthesize System Prompt and Context
    combined_context = "\n\n".join(context_chunks) if context_chunks else "No relevant context found."
    system_prompt = (
        "You are a helpful AI assistant. Use the following pieces of retrieved context "
        "to answer the user's question accurately. If you don't know the answer, say that you don't know.\n\n"
        f"--- START RETRIEVED CONTEXT ---\n{combined_context}\n--- END RETRIEVED CONTEXT ---"
    )

    # 5. Define an Asynchronous Generator to Stream Data Tokens
    async def ollama_stream_generator():
        ollama_payload = {
            "model": LLM_MODEL,
            "prompt": f"{system_prompt}\n\nUser Question: {data.question}\nAnswer:",
            "stream": True # Enable streaming delivery from Ollama
        }
        
        # Connect to Ollama with streaming enabled
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=ollama_payload) as resp:
                if resp.status_code != 200:
                    yield "Error: Failed to fetch stream generation from server."
                    return
                
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            parsed_line = json.loads(line)
                            token = parsed_line.get("response", "")
                            yield token  # Yield the generated token immediately to the client
                        except json.JSONDecodeError:
                            continue

    # Return a StreamingResponse object to keep the HTTP channel open [1]
    return StreamingResponse(ollama_stream_generator(), media_type="text/plain")
