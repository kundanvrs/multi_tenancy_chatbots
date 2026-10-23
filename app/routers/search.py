from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import get_db
import httpx

router = APIRouter(
    prefix="/api/chat",
    tags=["Similarity Search"]
)

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text:latest"
OLLAMA_LLM_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:7b"

# 1. API Schema Definitions
class QueryRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    question: str = Field(..., min_length=1)
    limit: int = Field(default=4, ge=1, le=10)

# 2. Similarity Search Query Route
@router.post("/search", status_code=status.HTTP_200_OK)
async def semantic_search(data: QueryRequest, db: Session = Depends(get_db)):
    safe_username = data.username.lower()
    table_name = f"tenant_{safe_username}"
    
    # 1. Verify that this specific tenant table exists
    table_check = db.execute(
        text("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :table)"),
        {"table": table_name}
    ).scalar()
    
    if not table_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data store found for user '{data.username}'. Please onboard and upload data first."
        )

    # 2. Convert incoming user question to a 768-dim vector using Ollama
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "input": data.question}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to vectorize search query via Ollama.")
                
            response_json = response.json()
            raw_embeddings = response_json.get("embeddings", [])
            
            # Ollama returns a list of lists [[x, y, z]]. Extract the first element safely.
            if not raw_embeddings or not isinstance(raw_embeddings[0], list):
                raise HTTPException(status_code=500, detail="Ollama returned an unexpected empty or malformed embedding structure.")
                
            query_vector = raw_embeddings[0] # Extracted the true flat array [x, y, z...]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama communication failure: {str(e)}")

    # 3. Query PostgreSQL using the Cosine Distance Operator (<=>)
    # 1 - distance converts the raw distance into a similarity score (closer to 1 = more similar)
    search_sql = f"""
    SELECT document_name, text_chunk, 1 - (embedding <=> :vector) AS similarity_score
    FROM {table_name}
    ORDER BY embedding <=> :vector
    LIMIT :limit;
    """
    
    try:
        result = db.execute(
            text(search_sql), 
            {
                "vector": str(query_vector), 
                "limit": data.limit
            }
        )
        
        # Format the database response cleanly for your chatbot interface
        retrieved_contexts = []
        for row in result:
            retrieved_contexts.append({
                "source_document": row.document_name,
                "text": row.text_chunk,
                "score": round(float(row.similarity_score), 4)
            })
            
        return {
            "status": "success",
            "query": data.question,
            "tenant": data.username,
            "matches": retrieved_contexts
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database retrieval operation failed: {str(e)}"
        )
