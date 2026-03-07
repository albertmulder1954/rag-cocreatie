from rag.vector_store import query_collection
from config import TOP_K_CHUNKS


def retrieve_context(query: str, top_k: int = TOP_K_CHUNKS) -> dict:
    """
    Retrieve relevant chunks for a query and format them into a context block.

    Returns:
        {
            "context_block": str,   formatted text to inject into Claude prompt
            "sources": list[dict],  deduplicated source list
            "chunks": list[dict],   raw chunk results
            "has_results": bool
        }
    """
    chunks = query_collection(query, top_k=top_k)

    if not chunks:
        return {
            "context_block": "",
            "sources": [],
            "chunks": [],
            "has_results": False,
        }

    # Build formatted context block
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[FRAGMENT {i} — Source: {chunk['filename']}, page ~{chunk['page_start']}]"
        )
        lines.append(chunk["text"])
        lines.append("")

    context_block = "\n".join(lines).strip()

    # Deduplicate sources by filename
    seen = set()
    sources = []
    for chunk in chunks:
        fn = chunk["filename"]
        if fn not in seen:
            seen.add(fn)
            sources.append({"filename": fn, "page_start": chunk["page_start"]})

    return {
        "context_block": context_block,
        "sources": sources,
        "chunks": chunks,
        "has_results": True,
    }


def assemble_user_message(question: str, context_block: str) -> str:
    """Wrap the user question with retrieved context for the Claude API call."""
    return (
        "AVAILABLE LITERATURE FRAGMENTS:\n"
        f"{context_block}\n\n"
        "USER QUESTION:\n"
        f"{question}\n\n"
        "Answer the question exclusively based on the fragments above. "
        "Cite the exact fragment text when making claims."
    )
