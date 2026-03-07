import re
import hashlib
from pypdf import PdfReader
import io

from config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_LENGTH


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> list[dict]:
    """Extract text page-by-page from a PDF."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page_num, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        cleaned = clean_text(raw)
        if cleaned.strip():
            pages.append({
                "page": page_num,
                "text": cleaned,
                "filename": filename,
            })
    return pages


def clean_text(raw: str) -> str:
    """Normalize PDF text: rejoin hyphenated words, collapse whitespace."""
    # Rejoin words split by hyphen at line break (e.g., "co-\ncreation" -> "co-creation")
    text = re.sub(r"-\n(\w)", r"-\1", raw)
    # Remove line breaks within sentences (keep double newlines as paragraph breaks)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    # Collapse more than two consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(pages: list[dict], chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Sliding window chunking over the full document text.
    Snaps boundaries to nearest sentence end to avoid mid-sentence cuts.
    """
    if not pages:
        return []

    filename = pages[0]["filename"]

    # Build full text and track character offset per page
    full_text = ""
    page_offsets = []  # (char_start, char_end, page_number)
    for p in pages:
        start = len(full_text)
        full_text += p["text"] + "\n\n"
        page_offsets.append((start, len(full_text), p["page"]))

    def char_to_page(char_pos: int) -> int:
        for start, end, page_num in page_offsets:
            if start <= char_pos < end:
                return page_num
        return page_offsets[-1][2]

    def snap_to_sentence_end(pos: int, direction: str = "forward") -> int:
        """Move pos to nearest sentence boundary ('. ', '! ', '? ', '\n')."""
        if direction == "forward":
            search_end = min(pos + 200, len(full_text))
            for i in range(pos, search_end):
                if full_text[i] in ".!?" and i + 1 < len(full_text) and full_text[i + 1] in " \n":
                    return i + 1
            return pos
        else:
            search_start = max(pos - 200, 0)
            for i in range(pos, search_start, -1):
                if full_text[i] in ".!?" and i + 1 < len(full_text) and full_text[i + 1] in " \n":
                    return i + 1
            return pos

    chunks = []
    chunk_index = 0
    pos = 0
    step = chunk_size - overlap

    while pos < len(full_text):
        end = min(pos + chunk_size, len(full_text))
        if end < len(full_text):
            end = snap_to_sentence_end(end)

        chunk_text = full_text[pos:end].strip()

        if len(chunk_text) >= MIN_CHUNK_LENGTH:
            chunk_id = hashlib.md5(f"{filename}_{pos}_{end}".encode()).hexdigest()
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "filename": filename,
                "page_start": char_to_page(pos),
                "char_start": pos,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        pos += step
        if pos >= len(full_text):
            break

    return chunks


def process_pdf(file_bytes: bytes, filename: str) -> tuple[list[dict], bool]:
    """
    Top-level function: extract, clean, chunk a PDF.
    Returns (chunks, is_empty) where is_empty=True means the PDF had no extractable text.
    """
    pages = extract_text_from_pdf(file_bytes, filename)
    if not pages:
        return [], True

    chunks = chunk_pages(pages)
    return chunks, False
