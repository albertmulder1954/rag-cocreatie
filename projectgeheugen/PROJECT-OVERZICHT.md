# Project Overzicht: RAG Co-creatie Decision Support

## Projectnaam
Co-Creation in Education — Decision Support (RAG)

## Eigenaar
Albert Mulder — WorldEmp India Private Limited

## GitHub Repository
- **URL**: https://github.com/albertmulder1954/rag-cocreatie
- **Branch**: main
- **Commits**: meerdere (merge, force Python 3.11, requirements updates)

## Lokaal pad
`C:\Users\alber\try out claude 6 maart\rag_cocreatie\`

## Wat is dit?
Een **Retrieval-Augmented Generation (RAG) applicatie** die wetenschappelijke vragen beantwoordt op basis van geüploade PDF-publicaties over co-creatie in het onderwijs. De tool geeft uitsluitend antwoorden op basis van de bronliteratuur, met verplichte citaten.

## Technologie Stack
| Component | Technologie |
|-----------|-------------|
| Frontend | Streamlit |
| AI Model | Claude claude-sonnet-4-6 via Anthropic API |
| Vector Database | ChromaDB (lokaal, persistent) |
| PDF Verwerking | pdfplumber of vergelijkbaar |
| Export | python-docx (Word documenten) |
| Taal | Python 3.11 |

## Architectuur
```
Streamlit UI (app.py)
    │
    ├── PDF Upload → pdf_processor.py → Chunking → vector_store.py (ChromaDB)
    │
    ├── Vraag → retriever.py (similarity search) → llm_client.py (Claude) → Antwoord
    │
    ├── Concept Extractie → concept_extractor.py → Merged concepts
    │
    └── Export → document_builder.py → .docx
```

## Modules

### rag/ — RAG Pipeline
| Module | Functie |
|--------|---------|
| `pdf_processor.py` | PDF inlezen en chunken (800 tokens, 150 overlap, min 100) |
| `vector_store.py` | ChromaDB: upsert chunks, list files, delete, reset |
| `retriever.py` | Similarity search: top-6 chunks, drempel 0.45 |
| `llm_client.py` | Claude API aanroep met system prompt |

### extraction/ — Concept Extractie
| Module | Functie |
|--------|---------|
| `concept_extractor.py` | Concepten extraheren uit tekst, samenvoegen over bestanden |

### export/ — Document Export
| Module | Functie |
|--------|---------|
| `document_builder.py` | Word document (.docx) genereren van Q&A en concepten |

### Configuratie (config.py)
| Parameter | Waarde |
|-----------|--------|
| CHUNK_SIZE | 800 |
| CHUNK_OVERLAP | 150 |
| MIN_CHUNK_LENGTH | 100 |
| TOP_K_CHUNKS | 6 |
| SIMILARITY_THRESHOLD | 0.45 |
| CHROMA_PERSIST_DIR | ./data/chroma_db |
| COLLECTION_NAME | literature |
| MODEL_NAME | claude-sonnet-4-6 |

### System Prompt — Strikte regels
1. **Alleen bron-gebaseerde antwoorden** — geen eigen kennis toevoegen
2. **Verplichte citaten** — elke claim met exact citaat + auteur, jaar, pagina
3. **Terminologische trouw** — alleen termen uit de bronliteratuur
4. **Transparantie** — expliciet aangeven als iets niet beantwoord kan worden
5. **Geen speculatie** — hedging language van auteurs behouden
6. **Antwoordstructuur**: direct antwoord → bewijs met citaten → bronnenlijst

## Bestandenindex
| Bestand | Beschrijving |
|---------|-------------|
| `app.py` | Streamlit hoofdapplicatie |
| `config.py` | Configuratie en system prompt |
| `rag/pdf_processor.py` | PDF chunking |
| `rag/vector_store.py` | ChromaDB operaties |
| `rag/retriever.py` | Context retrieval |
| `rag/llm_client.py` | Claude API client |
| `extraction/concept_extractor.py` | Concept extractie |
| `export/document_builder.py` | Word export |
| `requirements.txt` | Python dependencies |
| `runtime.txt` | Python versie (3.11) |
| `data/chroma_db/` | ChromaDB persistent storage |
| `.env` | API key (NIET in git) |
| `.env.example` | Voorbeeld env bestand |

## Gerelateerde projecten
| Project | Relatie |
|---------|--------|
| [co-creatie-in-het-onderwijs-en-ondersteuning-door-genai](https://github.com/albertmulder1954/co-creatie-in-het-onderwijs-en-ondersteuning-door-genai) | Papers over co-creatie; dezelfde publicaties als databron |
| `C:\Users\alber\OneDrive\Project Karen Konings\in claude te gebruiken publicaties\` | De 6 PDFs die als bron dienen |

## Openstaande acties
1. `.env.example` is gewijzigd maar niet gecommit
2. VS Code workspace bestand staat als untracked — niet essentieel voor git
3. ChromaDB data staat lokaal — bij her-installatie opnieuw PDFs uploaden
4. Geen README.md in de repo — overwegen om toe te voegen
5. Geen tests
