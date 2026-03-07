import chromadb
from chromadb.utils import embedding_functions

from config import CHROMA_PERSIST_DIR, COLLECTION_NAME, TOP_K_CHUNKS, SIMILARITY_THRESHOLD


def get_collection() -> chromadb.Collection:
    """Initialize persistent ChromaDB client and return the literature collection."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_chunks(chunks: list[dict]) -> None:
    """Upsert chunks into ChromaDB (idempotent via chunk_id)."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "filename": c["filename"],
                "page_start": c["page_start"],
                "chunk_index": c["chunk_index"],
                "char_start": c["char_start"],
            }
            for c in chunks
        ],
    )


def query_collection(query_text: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """
    Query ChromaDB and return top-k matching chunks above similarity threshold.
    ChromaDB cosine distance: 0 = identical, 2 = opposite. Lower is better.
    """
    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist <= SIMILARITY_THRESHOLD:
            chunks.append({
                "text": doc,
                "filename": meta["filename"],
                "page_start": meta["page_start"],
                "chunk_index": meta["chunk_index"],
                "distance": dist,
            })

    return chunks


def list_ingested_files() -> list[str]:
    """Return list of unique filenames currently in the collection."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.get(include=["metadatas"])
    filenames = list({m["filename"] for m in result["metadatas"]})
    return sorted(filenames)


def delete_file_chunks(filename: str) -> None:
    """Remove all chunks for a given filename from ChromaDB."""
    collection = get_collection()
    collection.delete(where={"filename": filename})


def reset_collection() -> None:
    """Delete and recreate the collection (start fresh)."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
