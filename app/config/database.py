from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_USER = "rag_user"
DB_PASSWORD = "SecurePassword123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "redmoon_platform"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """Dependency injector to yield DB sessions cleanly to routers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
