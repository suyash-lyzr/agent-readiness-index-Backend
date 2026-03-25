import fitz  # PyMuPDF
import re
from typing import Optional


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file using PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {str(e)}")

    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"[Page {page_num + 1}]\n{text}")

    doc.close()

    if not pages_text:
        raise ValueError("PDF appears to be empty or contains no extractable text (may be scanned image).")

    full_text = "\n\n".join(pages_text)

    # Clean up excessive whitespace
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r" {3,}", " ", full_text)

    # Truncate if too long (keep first ~10000 chars for LLM)
    if len(full_text) > 12000:
        full_text = full_text[:12000] + "\n\n[...content truncated for analysis...]"

    return full_text.strip()
