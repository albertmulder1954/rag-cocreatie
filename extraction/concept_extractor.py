import json
import anthropic

from config import ANTHROPIC_API_KEY, MODEL_NAME

CONCEPT_EXTRACTION_PROMPT = """You are analyzing scientific literature on co-creation in education.
Extract all key terms, definitions, and core concepts from the text below.

For each concept provide:
1. The term (exactly as used in the source)
2. The exact definition as given in the text (as a direct quote if possible)
3. The context (one sentence explaining how the concept is used)
4. An exact quote from the source text

Return your answer as a JSON array with this structure:
[
  {{
    "term": "co-creation",
    "definition": "exact definition from the text",
    "context": "how the concept is used in the literature",
    "exact_quote": "the exact sentence(s) from the source"
  }}
]

Rules:
- Extract minimum 5 and maximum 20 concepts
- If no explicit definition is given, use the most descriptive sentence about the concept
- Use only text from the provided source — do not add external knowledge
- Return ONLY the JSON array, no other text

Text to analyze:
{text_sample}
"""


def _sample_text(chunks: list[dict], max_chars: int = 6000) -> str:
    """Sample text from beginning, middle, and end of the document for breadth."""
    if not chunks:
        return ""

    texts = [c["text"] for c in chunks]
    full = "\n\n".join(texts)

    if len(full) <= max_chars:
        return full

    # Take thirds from beginning, middle, end
    third = max_chars // 3
    mid_start = len(full) // 2 - third // 2
    return (
        full[:third]
        + "\n\n[...]\n\n"
        + full[mid_start: mid_start + third]
        + "\n\n[...]\n\n"
        + full[-third:]
    )


def extract_concepts(filename: str, chunks: list[dict]) -> list[dict]:
    """
    Extract key concepts from a document's chunks via a separate Claude call.
    Returns list of concept dicts with source_filename attached.
    """
    text_sample = _sample_text(chunks)
    if not text_sample.strip():
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = CONCEPT_EXTRACTION_PROMPT.format(text_sample=text_sample)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        concepts = json.loads(raw)
        for c in concepts:
            c["source_filename"] = filename
        return concepts

    except (json.JSONDecodeError, IndexError, Exception):
        return []


def merge_concepts_across_files(concepts_by_file: dict[str, list[dict]]) -> list[dict]:
    """
    Merge concept lists from multiple files into one flat list.
    Groups entries by term (case-insensitive) and notes when multiple sources cover the same concept.
    """
    merged: dict[str, dict] = {}

    for filename, concepts in concepts_by_file.items():
        for concept in concepts:
            key = concept["term"].lower().strip()
            if key not in merged:
                merged[key] = {**concept, "sources": [filename]}
            else:
                if filename not in merged[key]["sources"]:
                    merged[key]["sources"].append(filename)

    result = []
    for entry in merged.values():
        entry["source_filename"] = ", ".join(entry["sources"])
        result.append(entry)

    return sorted(result, key=lambda x: x["term"].lower())
