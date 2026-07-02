from typing import Protocol

from policymind.documents.models import ParsedDocument


class DocumentParser(Protocol):
    supported_mime_types: frozenset[str]

    def parse(self, content: bytes, filename: str) -> ParsedDocument: ...


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {}

    def register(self, parser: DocumentParser) -> None:
        for mime in parser.supported_mime_types:
            self._parsers[mime] = parser

    def resolve(self, mime_type: str) -> DocumentParser:
        parser = self._parsers.get(mime_type)
        if parser is None:
            raise ValueError(f"No parser registered for MIME type: {mime_type}")
        return parser

    def parse(self, mime_type: str, content: bytes, filename: str) -> ParsedDocument:
        parser = self.resolve(mime_type)
        return parser.parse(content, filename)
