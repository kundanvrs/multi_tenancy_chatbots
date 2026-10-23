

# Multi-Domain RAG Chatbot Platform 

## Overview

**Chatbot Platform** is a multi-tenant, multi-domain AI chatbot architecture powered by Large Language Models (LLMs), vector embeddings, semantic search, and dynamically isolated tenant storage.

The platform enables rapid onboarding of new business domains such as **Dental**, **FoodPlaza**, **CBSE**, and other knowledge-driven applications while maintaining complete data isolation between tenants. Each tenant has its own document ingestion pipeline, vector storage, retrieval scope, and user experience configuration.

### Technology Stack

- FastAPI
- LangChain
- PostgreSQL
- pgvector
- Ollama
- Qwen 2.5 7B
- Nomic Embed Text
- Retrieval-Augmented Generation (RAG)

---

# 🚀 Architecture: How Multi-Domain is Achieved

The platform isolates tenant data while sharing a centralized AI processing pipeline.

## 1. Dynamic Schema Isolation (Multi-Tenancy)

When a new tenant is onboarded, the platform automatically provisions tenant-specific data structures using the tenant identifier (`username`).

Benefits:

- Complete tenant data isolation
- Independent document repositories
- Dedicated vector search spaces
- Easy domain onboarding

## 2. Domain-Specific Embeddings

Uploaded documents such as:

- PDF
- TXT
- CSV

are processed through the ingestion pipeline.

### Workflow

1. Document extraction
2. Text chunking
3. Embedding generation
4. Vector storage in PostgreSQL (`pgvector`)

Each vector remains isolated within the tenant workspace.

## 3. Contextual Retrieval

During a chat session:

1. UI sends tenant context.
2. Backend performs vector similarity search.
3. Relevant document chunks are retrieved.
4. Context is injected into the LLM prompt.
5. Response is generated and streamed back to the user.

This prevents cross-tenant knowledge leakage while maintaining a centralized AI architecture.

---

# 🛠️ Database Setup (pgvector)

The backend requires PostgreSQL with the `pgvector` extension enabled.

```sql
-- Connect as postgres user
psql -U postgres

-- Create application database
CREATE DATABASE ur_platform;

-- Create application user
CREATE USER rag_user WITH PASSWORD 'Password123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ur_platform TO rag_user;

-- Connect to the database
\c ur_platform

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Exit
\q
```

---

# ⚙️ Backend Installation & Running

## 1. Create Virtual Environment

```bash
python -m venv .venv
```

## 2. Activate Virtual Environment

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Application

### Local Development

```bash
uvicorn main:app --port 8000 --reload
```

### External Network Access

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Documentation

```text
http://127.0.0.1:8000/docs
```

---

# 🤖 AI Models

## LLM

```text
qwen2.5:7b
```

Responsibilities:

- Response generation
- Question answering
- Context understanding
- RAG synthesis

## Embedding Model

```text
nomic-embed-text:latest
```

Responsibilities:

- Semantic embeddings
- Similarity search
- Context retrieval

## Vector Database

```text
PostgreSQL + pgvector
```

---

# 🌐 Frontend Configuration

Configure the backend endpoint inside `index.html`.

## Local Development

```javascript
const BACKEND_URL = "http://127.0.0.1:8000";
```

## Network Deployment

```javascript
const BACKEND_URL = "http://0.0.0.0:8000";
```

---

# 👥 Onboarding a New Tenant / Domain

Supported examples:

- Dental
- FoodPlaza
- CBSE
- Academy
- Healthcare
- Retail

---

## Step 1: Tenant Registration

Register a tenant through the onboarding API.

### Endpoint

```http
POST /api/tenant/onboard
```

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

The onboarding process automatically:

- Creates tenant metadata
- Creates isolated storage structures
- Prepares vector storage for ingestion

---

## Step 2: Upload Documents

Upload tenant-specific documents using:

```http
POST /api/data/upload
```

Supported formats:

- PDF
- TXT
- CSV

The ingestion pipeline performs:

- Text extraction
- Chunking
- Embedding generation
- Vector storage

---

## Step 3: Configure Frontend Workspace

Register a new tenant configuration in the frontend.

### Example: Dental Assistant

```javascript
dental: {
  label: "Dental",
  title: "Dental Clinic Assistant",
  accent: "#0d9488",
  accentDark: "#0f766e",
  soft: "rgba(13, 148, 136, .16)",
  greeting:
    "Welcome to the Dental Clinic Assistant. Ask about treatments, appointments, pricing, or uploaded clinical documentation."
}
```

---

## Step 4: Start Chatting

After onboarding and ingestion:

1. Reload the frontend application.
2. Select the tenant workspace.
3. Start chatting with your domain-specific knowledge base.

---

# 🔌 API Endpoints

## Tenant Management

### Onboard New Tenant

```http
POST /api/tenant/onboard
```

Creates a new tenant workspace and initializes required infrastructure.

---

## Data Ingestion

### Upload Documents

```http
POST /api/data/upload
```

Uploads documents and generates vector embeddings.

---

## Semantic Search & Streaming Generation

### Semantic Stream Chat

```http
POST /api/chat/stream
```

Workflow:

1. Receive user query
2. Execute similarity search
3. Retrieve contextual chunks
4. Construct augmented prompt
5. Stream generated response

---

## Health Check

### Verify Service Availability

```http
GET /
```

Returns backend service health status.

---

# 📚 API Documentation

Swagger Documentation:

```text
http://127.0.0.1:8000/docs
```

---

# ✅ Core Features

- Multi-Tenant Architecture
- Dynamic Tenant Onboarding
- Domain-Specific Knowledge Bases
- PostgreSQL + pgvector
- Semantic Search
- Streaming Responses
- Retrieval-Augmented Generation (RAG)
- FastAPI Backend
- LangChain Integration
- Tenant-Isolated Vector Storage
- Ollama Model Integration

---

# ✅ Domain Examples

| Domain | Use Cases |
|----------|-----------|
| Dental | Treatments, pricing, appointments |
| FoodPlaza | Menus, offers, inventory, customer support |
| CBSE | Educational documents and curriculum guidance |
| Academy | Courses, study materials, FAQs |
| Healthcare | Clinical documentation assistance |
| Retail | Product catalogs and policy knowledge bases |

---

# 📌 Project Summary

The  Platform provides a scalable multi-domain Retrieval-Augmented Generation (RAG) architecture that enables organizations to rapidly onboard new business domains while maintaining complete tenant isolation, semantic retrieval capabilities, and AI-powered conversational experiences.
