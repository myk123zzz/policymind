def test_markdown_parser_extracts_headings() -> None:
    """Markdown 解析器提取标题层级。"""
    from policymind.documents.parsers.markdown import MarkdownParser

    content = b"# Title\n\n## Section 1\n\nParagraph text here.\n\n## Section 2\n\nMore text."
    parser = MarkdownParser()
    result = parser.parse(content, filename="test.md")

    assert result.title == "Title"
    assert result.page_count == 1
    assert len(result.blocks) == 2  # section1 text, section2 text


def test_markdown_parser_title_fallback() -> None:
    """无标题时用文件名作为回退。"""
    from policymind.documents.parsers.markdown import MarkdownParser

    content = b"Just some text\n\nwithout any heading."
    parser = MarkdownParser()
    result = parser.parse(content, filename="notes.md")

    assert result.title is not None


def test_parser_registry_resolves_by_mime() -> None:
    """ParserRegistry 根据 MIME 类型选择解析器。"""
    from policymind.documents.parsers.markdown import MarkdownParser
    from policymind.documents.parsers.registry import ParserRegistry

    registry = ParserRegistry()
    registry.register(MarkdownParser())

    parser = registry.resolve("text/markdown")
    assert parser is not None
    assert "text/markdown" in parser.supported_mime_types


def test_parser_registry_unknown_mime_raises() -> None:
    """未知 MIME 类型抛出异常。"""
    import pytest

    from policymind.documents.parsers.registry import ParserRegistry

    registry = ParserRegistry()
    with pytest.raises(ValueError, match="parser"):
        registry.resolve("application/x-unknown")
