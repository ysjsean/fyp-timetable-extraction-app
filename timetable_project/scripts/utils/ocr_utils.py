import re

def clean_text(s: str) -> str:
    """
    Cleans OCR text by removing special characters and normalizing symbols.
    """
    s = s.replace("£", "E").replace("—", "-").replace("–", "-").strip()
    s = re.sub(r"[^\x20-\x7E]", "", s)  # Remove non-ASCII
    return s.upper()
