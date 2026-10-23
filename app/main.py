from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import tenant, ingestion, search, ollama_search, stream_search, update_docs  # Import your route modules

app = FastAPI(
    title="Scalable Multi-Tenant RAG Platform",
    version="1.0.0"
)

# Allow cross-origin requests from frontends/chatbot widgets
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Plug in routers dynamically
app.include_router(tenant.router)
app.include_router(ingestion.router)
app.include_router(update_docs.router)
# app.include_router(search.router)
#app.include_router(ollama_search.router)  # Include the Ollama search router
app.include_router(stream_search.router)  # Include the Ollama search router

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "RAG API Gateway"}
