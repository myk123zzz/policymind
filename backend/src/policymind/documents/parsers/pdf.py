# mypy: ignore-errors
from pathlib import Path

import pymupdf

from policymind.documents.models import DocumentBlock, ParsedDocument


class PDFParser:
    supported_mime_types: frozenset[str] = frozenset({"application/pdf"})

    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        doc = pymupdf.open(stream=content, filetype="pdf")
        title: str = doc.metadata.get("title") or Path(filename).stem  # type: ignore[union-attr]
        blocks: list[DocumentBlock] = []

        page_count: int = doc.page_count  # type: ignore[union-attr]
        for page_num in range(page_count):
            page = doc[page_num]
            text: str = page.get_text("text")
            if text.strip():
                blocks.append(
                    DocumentBlock(
                        text=text.strip(),
                        page_number=page_num + 1,
                        block_type="text",
                    )
                )

        doc.close()
        return ParsedDocument(
            title=title,
            page_count=page_count,
            blocks=blocks,
        )
