"""PDF text extraction with page-level chunking using PyMuPDF."""

import re
from pathlib import Path

import fitz  # PyMuPDF

DOI_PATTERN = re.compile(r"(10\.\d{4,}/[^\s]+)")


def extract_text(pdf_path: str | Path) -> list[dict]:
    """Extract text from a PDF, returning a list of page dicts.

    Returns:
        List of {"page": int, "text": str} where page is 1-indexed.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages.append({"page": i + 1, "text": text})
    return pages


def extract_doi(pages: list[dict]) -> str | None:
    """Extract DOI from the first page of a PDF."""
    if not pages:
        return None
    first_page_text = pages[0]["text"]
    match = DOI_PATTERN.search(first_page_text)
    if match:
        doi = match.group(1).rstrip(".,;)")
        return doi
    return None


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[dict]:
    """Split page-level text into overlapping chunks preserving paragraph boundaries.

    Args:
        pages: Output from extract_text().
        chunk_size: Target chunk size in characters.
        overlap: Overlap between consecutive chunks in characters.

    Returns:
        List of {
            "chunk_id": int,
            "text": str,
            "page_start": int,
            "page_end": int,
            "token_estimate": int,
        }
    """
    if not pages:
        return []

    # Build a flat list of paragraphs with page attribution
    paragraphs: list[dict] = []
    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]
        # Split on double newlines (paragraph boundaries) or single newlines followed by
        # an uppercase letter (common in PDFs)
        raw_paras = re.split(r"\n\s*\n", text)
        for para in raw_paras:
            para = para.strip()
            if para:
                paragraphs.append({"text": para, "page": page_num})

    # Assemble chunks from paragraphs
    chunks: list[dict] = []
    chunk_id = 0
    buf = ""
    page_start = paragraphs[0]["page"] if paragraphs else 1
    page_end = page_start
    para_idx = 0

    while para_idx < len(paragraphs):
        para = paragraphs[para_idx]

        candidate = (buf + "\n\n" + para["text"]).strip() if buf else para["text"]

        if len(candidate) <= chunk_size or not buf:
            # Add paragraph to current buffer
            buf = candidate
            page_end = para["page"]
            para_idx += 1
        else:
            # Flush current buffer as a chunk
            chunks.append({
                "chunk_id": chunk_id,
                "text": buf,
                "page_start": page_start,
                "page_end": page_end,
                "token_estimate": len(buf) // 4,
            })
            chunk_id += 1

            # Back up to create overlap: find a split point in the buffer
            if overlap > 0 and len(buf) > overlap:
                overlap_text = buf[-overlap:]
                # Start next chunk with the overlap portion
                buf = overlap_text
                page_start = page_end
            else:
                buf = ""
                page_start = para["page"]
            # Do NOT advance para_idx - re-process current paragraph against new buffer

    # Flush remaining buffer
    if buf.strip():
        chunks.append({
            "chunk_id": chunk_id,
            "text": buf,
            "page_start": page_start,
            "page_end": page_end,
            "token_estimate": len(buf) // 4,
        })

    return chunks
