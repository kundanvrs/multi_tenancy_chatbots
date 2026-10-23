# routers/ingestion.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import get_db
import pypdf
import io
import httpx

router = APIRouter(
    prefix="/api/data",
    tags=["Data Ingestion"]
)

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text:latest"

def chunk_text(text: str, chunk_size_chars: int = 4000, chunk_overlap_chars: int = 800) -> list[str]:
    """
    Splits text into chunks using characters rather than words.
    4000 characters is roughly ~1000 tokens, which easily fits 
    within the 2048 token limit of nomic-embed-text.
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size_chars
        chunk = text[start:end]
        
        # Avoid cutting in the exact middle of a word if possible
        if end < text_length and not text[end].isspace():
            last_space = chunk.rfind(' ')
            if last_space != -1:
                chunk = chunk[:last_space]
                end = start + last_space
                
        if chunk.strip():
            chunks.append(chunk.strip())
            
        start = end - chunk_overlap_chars
        
    return chunks


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    username: str = Form(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    safe_username = username.lower()
    table_name = f"tenant_{safe_username}"
    
    # 1. Verify Table Existence
    table_check = db.execute(
        text("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :table)"),
        {"table": table_name}
    ).scalar()
    
    if not table_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' does not exist. Please onboard this user first."
        )

    # 2. Extract Document Text
    file_content = await file.read()
    document_text = ""
    
    if file.filename.endswith(".pdf"):
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    document_text += page_text + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF file: {str(e)}")
    elif file.filename.endswith((".txt", ".json")):
        document_text = file_content.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Upload .pdf or .txt")

    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Document text content is empty.")

    chunks = chunk_text(document_text)

    # 3. Vectorize text natively via Ollama API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "input": chunks}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Ollama embedding failure: {response.text}")
                
            embeddings = response.json().get("embeddings", [])

        # 4. Save Embeddings via safe database transactions
        insert_sql = f"""
        INSERT INTO {table_name} (document_name, text_chunk, embedding)
        VALUES (:doc_name, :chunk, :vector);
        """
        
        with db.begin_nested():
            for i, chunk in enumerate(chunks):
                db.execute(
                    text(insert_sql),
                    {
                        "doc_name": file.filename,
                        "chunk": chunk,
                        "vector": str(embeddings[i])  # 768 float array
                    }
                )
        db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully vectorized {len(chunks)} elements into '{table_name}'."
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
