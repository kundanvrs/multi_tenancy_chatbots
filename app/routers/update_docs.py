# routers/update_docs.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from config.database import get_db
import pypdf
import io
import httpx

router = APIRouter(
    prefix="/api/update_db",
    tags=["DB Update"]
)


def provision_tenant_table(db: Session, safe_username: str) -> str:
    table_name = f"tenant_{safe_username}"
    
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        document_name TEXT,
        text_chunk TEXT NOT NULL,
        embedding VECTOR(768),  -- Modified to match nomic-embed-text dimensions
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_index_sql = f"""
    CREATE INDEX IF NOT EXISTS {table_name}_vector_hnsw_idx 
    ON {table_name} USING hnsw (embedding vector_cosine_ops);
    """
    
    db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    db.execute(text(create_table_sql))
    db.execute(text(create_index_sql))
    db.commit()
    
    return table_name



def drop_all_tenant_tables(db: Session) -> list[str]:
    """
    Finds all tables starting with 'tenant_' and drops them cleanly.
    Returns a list of table names that were deleted.
    """
    # 1. Query the PostgreSQL system catalog to find active tenant tables safely
    find_tables_sql = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' AND tablename LIKE 'tenant_%';
    """
    
    result = db.execute(text(find_tables_sql))
    tables_to_drop = [row[0] for row in result]
    
    dropped_tables = []
    
    # 2. Execute DROP TABLE statements iteratively within a controlled block
    if tables_to_drop:
        # Wrap in a transactional block to ensure atomicity
        with db.begin_nested():
            for table in tables_to_drop:
                db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                dropped_tables.append(table)
        db.commit()
        
    return dropped_tables
