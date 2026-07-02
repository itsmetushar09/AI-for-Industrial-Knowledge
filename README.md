# INDUS AI – Industrial Knowledge Intelligence Platform

> AI-powered enterprise knowledge assistant for industrial organizations using Retrieval-Augmented Generation (RAG).

![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Database](https://img.shields.io/badge/Database-Supabase-success)
![AI](https://img.shields.io/badge/AI-RAG%20%7C%20OpenAI-orange)

---

## Overview

INDUS AI is an enterprise-grade AI platform that transforms scattered industrial documents into an intelligent, searchable knowledge system.

Organizations often store manuals, SOPs, inspection reports, maintenance logs, safety procedures, compliance documents, and engineering drawings across multiple disconnected systems. Finding the right information during critical operations is time-consuming and error-prone.

INDUS AI solves this problem using Retrieval-Augmented Generation (RAG), enabling users to upload industrial documents and ask natural language questions while receiving contextual, source-cited responses.

---

## Problem Statement

Industrial organizations struggle with:

- Knowledge scattered across multiple systems
- Time-consuming manual document search
- Lack of contextual document intelligence
- Compliance and audit difficulties
- Loss of organizational knowledge
- Slow maintenance decision-making

INDUS AI centralizes organizational knowledge into an AI-powered assistant.

---

## Key Features

### AI Copilot

- Natural language conversations
- Context-aware responses
- Document-grounded answers
- Confidence scores
- Source citations
- Page-level references

---

### Document Intelligence

Supports:

- PDF
- DOCX
- TXT
- CSV
- XLSX
- Images (OCR Ready)

Features:

- Drag & Drop Upload
- Automatic Processing
- Metadata Extraction
- Semantic Search
- Document Preview

---

### Retrieval-Augmented Generation (RAG)

Pipeline:

Document Upload
↓

Text Extraction
↓

Chunking
↓

Embedding Generation
↓

Vector Storage (pgvector)
↓

Similarity Search
↓

LLM Response
↓

Source Citation

---

### Enterprise Dashboard

- Document Analytics
- Upload Statistics
- AI Usage
- Maintenance Overview
- Compliance Status
- Department Insights

---

### Knowledge Graph

Interactive visualization connecting:

- Equipment
- Departments
- Procedures
- Regulations
- Maintenance Records
- Technical Documents

---

### Security

- Supabase Authentication
- JWT Verification
- Role-Based Access Control
- Secure File Storage
- Protected APIs

---

## Technology Stack

### Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui
- TanStack Query
- React Router
- Axios
- Framer Motion

---

### Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- Pydantic

---

### Database

- Supabase PostgreSQL
- pgvector
- Supabase Storage

---

### AI Stack

- Gemini
- LangChain
- Retrieval-Augmented Generation
- PyMuPDF
- tiktoken

---

## System Architecture

```
React Frontend
        │
        ▼
Axios API Layer
        │
        ▼
FastAPI Backend
        │
        ├───────────── Authentication
        ├───────────── File Upload
        ├───────────── Document Processing
        ├───────────── RAG Pipeline
        ├───────────── Embedding Service
        └───────────── Chat Service
                     │
                     ▼
            Supabase PostgreSQL
            pgvector
            Storage
                     │
                     ▼
               OpenAI GPT
```

---

## AI Workflow

```
User Uploads Document
        │
        ▼
Extract Text
        │
        ▼
Chunk Document
        │
        ▼
Generate Embeddings
        │
        ▼
Store in pgvector
        │
        ▼
User asks question
        │
        ▼
Semantic Search
        │
        ▼
Relevant Chunks
        │
        ▼
OpenAI GPT
        │
        ▼
Response with Citations
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| /health | GET | Health Check |
| /upload | POST | Upload Document |
| /documents | GET | List Documents |
| /documents/{id} | GET | Document Details |
| /documents/search | GET | Semantic Search |
| /chat | POST | AI Chat |
| /chat/history | GET | Conversation History |
| /analytics | GET | Dashboard Analytics |

---

## Roles

- Administrator
- Plant Manager
- Maintenance Engineer
- Safety Officer
- Operator

---

---

## Installation

### Frontend

```bash
npm install
npm run dev
```

### Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

-

---

**INDUS AI — Transforming Industrial Knowledge into Intelligent Decisions.**
