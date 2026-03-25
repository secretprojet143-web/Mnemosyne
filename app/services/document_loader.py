from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader


class DocumentLoader:
    def load_file(self, path: str) -> Optional[str]:
        file_path = Path(path)

        if not file_path.exists() or not file_path.is_file():
            return None

        suffix = file_path.suffix.lower()

        try:
            if suffix in [".txt", ".md", ".py", ".js", ".json", ".csv", ".html", ".htm"]:
                text = file_path.read_text(encoding="utf-8", errors="ignore")

                if suffix in [".html", ".htm"]:
                    soup = BeautifulSoup(text, "html.parser")
                    return soup.get_text(separator="\n")

                return text

            if suffix == ".pdf":
                reader = PdfReader(str(file_path))
                pages = [page.extract_text() or "" for page in reader.pages]
                return "\n".join(pages)

            if suffix == ".docx":
                doc = Document(str(file_path))
                return "\n".join(p.text for p in doc.paragraphs)

        except Exception:
            return None

        return None
