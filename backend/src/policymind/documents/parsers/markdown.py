from pathlib import Path

from policymind.documents.models import DocumentBlock, ParsedDocument


class MarkdownParser:
    supported_mime_types: frozenset[str] = frozenset({"text/markdown", "text/plain"})

    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        text = content.decode("utf-8", errors="replace")
        lines = text.split("\n")
        blocks: list[DocumentBlock] = []
        title = Path(filename).stem

        current_heading: tuple[str, ...] = ()
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                self._flush(current_lines, current_heading, blocks)
                title = stripped[2:].strip()
                current_heading = (title,)
            elif stripped.startswith("## "):
                self._flush(current_lines, current_heading, blocks)
                section = stripped[3:].strip()
                current_heading = (title, section) if title else (section,)
            elif stripped == "" and current_lines:
                self._flush(current_lines, current_heading, blocks)
                current_heading = current_heading
            else:
                current_lines.append(line)

        self._flush(current_lines, current_heading, blocks)

        return ParsedDocument(
            title=title,
            page_count=1,
            blocks=blocks,
            metadata={},
        )

    @staticmethod
    def _flush(
        lines: list[str],
        heading: tuple[str, ...],
        blocks: list[DocumentBlock],
    ) -> None:
        text = "\n".join(lines).strip()
        if text:
            blocks.append(
                DocumentBlock(
                    text=text,
                    page_number=1,
                    block_type="text",
                    heading_path=heading,
                )
            )
        lines.clear()
