# CLAUDE.md -- RAG Co-Creatie Decision Support

## Project Identity

| Field | Value |
|-------|-------|
| **Name** | Co-Creation in Education -- Decision Support (RAG) |
| **Repo** | `albertmulder1954/rag-cocreatie` (branch: `main`) |
| **Owner** | Albert Mulder (WorldEmp India Private Limited) |
| **Local path** | `C:\Users\alber\try out claude 6 maart\rag_cocreatie\` |
| **Python** | 3.11 |
| **Role of Claude** | Albert does not code. Claude writes, maintains, and deploys all code. |

## What This Project Does

A Streamlit-based RAG application that answers scientific questions about **co-creation in education** using uploaded PDF literature. All answers are strictly source-based with mandatory citations. No external knowledge is added.

**User workflow:**
1. Upload scientific PDFs via the sidebar
2. PDFs are chunked, embedded, and stored in ChromaDB
3. Key concepts are automatically extracted per document
4. User asks questions -- relevant chunks are retrieved and sent to Claude with a strict system prompt
5. Session (Q&A + concepts) can be exported as a Word document (.docx)

## Tech Stack

| Component | Technology | Details |
|-----------|------------|---------|
| Frontend | Streamlit | Single-page app in `app.py` |
| LLM | Anthropic Claude (claude-sonnet-4-6) | Via `anthropic` Python SDK |
| Vector DB | ChromaDB | Local persistent storage in `data/chroma_db/` |
| Embeddings | `all-MiniLM-L6-v2` | Via `sentence-transformers`, used by ChromaDB |
| PDF parsing | `pypdf` | Text extraction + cleaning + sentence-aware chunking |
| Export | `python-docx` | Generates formatted Word reports |
| Config | `python-dotenv` | API key loaded from `.env` |

## Architecture

```
app.py (Streamlit UI)
  |
  +-- rag/pdf_processor.py    --> PDF text extraction + chunking
  +-- rag/vector_store.py     --> ChromaDB upsert, query, delete, reset
  +-- rag/retriever.py        --> Similarity search + context formatting
  +-- rag/llm_client.py       --> Claude API calls with system prompt
  |
  +-- extraction/concept_extractor.py  --> LLM-based concept extraction
  +-- export/document_builder.py       --> Word document generation
  |
  +-- config.py               --> All settings, thresholds, system prompt
```

## File Index

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application (UI, tabs, session state) |
| `config.py` | Configuration constants + system prompt |
| `rag/pdf_processor.py` | PDF reading, text cleaning, sliding-window chunking |
| `rag/vector_store.py` | ChromaDB collection management (upsert, query, delete, reset) |
| `rag/retriever.py` | Retrieval: query vector store, format context block for Claude |
| `rag/llm_client.py` | Anthropic API client, sends RAG-augmented prompts |
| `extraction/concept_extractor.py` | Extracts key terms/definitions via separate Claude call |
| `export/document_builder.py` | Builds .docx with title, concepts table, Q&A, references |
| `requirements.txt` | Python dependencies |
| `runtime.txt` | Python version spec (3.11) |
| `.env` | API key (NEVER commit -- already in .gitignore) |
| `.env.example` | Template for `.env` |
| `data/chroma_db/` | ChromaDB persistent storage (gitignored) |

## Configuration Parameters (config.py)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MODEL_NAME` | `claude-sonnet-4-6` | LLM model for Q&A and concept extraction |
| `CHUNK_SIZE` | 800 | Characters per chunk |
| `CHUNK_OVERLAP` | 150 | Overlap between consecutive chunks |
| `MIN_CHUNK_LENGTH` | 100 | Discard chunks shorter than this |
| `TOP_K_CHUNKS` | 6 | Number of chunks retrieved per query |
| `SIMILARITY_THRESHOLD` | 0.45 | ChromaDB cosine distance cutoff (lower = more similar) |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Vector database location |
| `COLLECTION_NAME` | `literature` | ChromaDB collection name |

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 3. Run the app
streamlit run app.py
```

## System Prompt Rules (for Q&A)

The system prompt in `config.py` enforces strict scientific rigor:

1. **Source-based answers only** -- no external knowledge, ever
2. **Mandatory citations** -- every claim needs an exact quote with author, year, page
3. **Terminological fidelity** -- use only terms from the uploaded literature
4. **Transparency** -- explicitly state when a question cannot be answered
5. **No speculation** -- preserve hedging language from authors
6. **Answer structure** -- direct answer, then evidence with citations, then source list

## Key Design Decisions

- **Sentence-aware chunking**: Chunk boundaries snap to nearest sentence end (looks up to 200 chars forward) to avoid mid-sentence cuts
- **Idempotent upserts**: Chunk IDs are MD5 hashes of `filename_charstart_charend`, so re-uploading the same PDF is safe
- **Concept extraction sampling**: For large documents, samples text from beginning, middle, and end (max 6000 chars) to get breadth
- **Cosine distance threshold**: Chunks with distance > 0.45 are discarded to avoid irrelevant context
- **Session state sync**: On startup, `list_ingested_files()` syncs session state with what is actually in ChromaDB

## Related Projects

| Project | Relationship |
|---------|-------------|
| `albertmulder1954/co-creatie-in-het-onderwijs-en-ondersteuning-door-genai` | Contains the co-creation papers used as data sources |

## Known Limitations

- No OCR support -- scanned PDFs without text layers are rejected with a warning
- ChromaDB data is local only -- re-upload PDFs after reinstall
- No authentication -- intended for single-user local use
- No tests exist yet
- No error retry logic on Anthropic API calls
