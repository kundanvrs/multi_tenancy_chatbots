import sys
from sqlalchemy import create_engine, Column, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

# 1. Database Connection Configuration
# Replace with your actual server IP and the password you set up earlier
DB_USER = "rag_user"
DB_PASSWORD = "SecurePassword123"
DB_HOST = "localhost"  # Change to your server's public IP if running remotely
DB_PORT = "5432"
DB_NAME = "redmoon_platform"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Initialize SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 2. Define the School FAQ Schema
class SchoolFAQ(Base):
    __tablename__ = "tennant_school_dps"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # e.g., "Admissions", "Fees", "Transport"
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    # 1536 dimensions matches standard OpenAI models (e.g., text-embedding-3-small)
    # If using a local model like BGE or MiniLM, change 1536 to its specific output dimensions (e.g., 384 or 768)
    embedding = Column(Vector(1536))

# 3. Execution Block to Provision the Table and Index
def initialize_database():
    print("🔄 Connecting to the database...")
    
    # Core safety check: Ensure the vector extension is active inside this database instance
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
    print("✅ Verified pgvector extension.")

    print("🛠️ Creating tables...")
    # Create the table based on the schema class defined above
    Base.metadata.create_all(bind=engine)
    print("✅ 'tennant_school_dps' table created successfully.")
    
    # Add an isolated HNSW index directly on the vector column for ultra-fast cosine similarity lookups
    print("⚡ Building HNSW index for optimized similarity search...")
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS tennant_school_dps_vector_hnsw_idx "
                "ON tennant_school_dps USING hnsw (embedding vector_cosine_ops);"
            ))
    print("✅ HNSW index active.")

if __name__ == "__main__":
    # Import text utility required for raw SQL extension checks
    from sqlalchemy import text
    
    try:
        initialize_database()
        print("\n🎉 Success! The school FAQ vector store is ready for data ingestion.")
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}", file=sys.stderr)
