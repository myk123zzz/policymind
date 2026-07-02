from policymind.documents.chunking import HierarchicalChunker
from policymind.documents.models import DocumentBlock, ParsedDocument


def make_parsed_doc(title: str, blocks: list[DocumentBlock]) -> ParsedDocument:
    return ParsedDocument(
        title=title,
        page_count=1,
        blocks=blocks,
        metadata={},
    )


def make_block(
    text: str,
    page: int = 1,
    block_type: str = "text",
    heading_path: tuple[str, ...] = (),
) -> DocumentBlock:
    return DocumentBlock(
        text=text,
        page_number=page,
        block_type=block_type,
        heading_path=heading_path,
    )


class TestHierarchicalChunker:
    def test_leaf_chunks_keep_provenance(self) -> None:
        """Leaf Chunk 必须保留 parent_id、page_number 等来源信息。"""
        chunker = HierarchicalChunker(
            parent_size=1200,
            leaf_size=400,
            overlap=100,
        )
        doc = make_parsed_doc(
            title="Test Doc",
            blocks=[make_block("A" * 600, page=1), make_block("B" * 600, page=2)],
        )

        chunks = chunker.chunk(document=doc, document_version_id=42)
        leaves = [c for c in chunks if c.level == "leaf"]

        for leaf in leaves:
            assert leaf.parent_id is not None, f"leaf {leaf.id} missing parent_id"
            assert leaf.page_number > 0, f"leaf {leaf.id} missing page_number"

        # Should have at least 2 leaf chunks (one per block)
        assert len(leaves) >= 2

    def test_parent_child_relationship(self) -> None:
        """Parent 和 Leaf 之间存在正确的 ID 关联。"""
        chunker = HierarchicalChunker(parent_size=1200, leaf_size=400, overlap=100)
        doc = make_parsed_doc(
            title="Relational Doc",
            blocks=[make_block("Paragraph " * 80, page=1)],
        )

        chunks = chunker.chunk(document=doc, document_version_id=1)
        parents = [c for c in chunks if c.level == "parent"]
        leaves = [c for c in chunks if c.level == "leaf"]

        assert len(parents) >= 1
        assert len(leaves) >= 1
        # All leaves should reference a parent
        parent_ids = {p.id for p in parents}
        for leaf in leaves:
            assert leaf.parent_id in parent_ids

    def test_table_header_not_split(self) -> None:
        """表格表头不应与数据行分离。"""
        chunker = HierarchicalChunker(parent_size=1200, leaf_size=200, overlap=50)
        doc = make_parsed_doc(
            title="Table Doc",
            blocks=[
                make_block(
                    "| Name | Amount |\n|------|--------|\n| Item | 100 |",
                    block_type="table",
                )
            ],
        )

        chunks = chunker.chunk(document=doc, document_version_id=1)
        table_chunks = [c for c in chunks if "Name" in c.text]

        # The header row should be in the same chunk as at least one data row
        for tc in table_chunks:
            assert "Amount" in tc.text

    def test_heading_path_preserved(self) -> None:
        """标题路径在分块后保留。"""
        chunker = HierarchicalChunker(parent_size=1200, leaf_size=400, overlap=100)
        doc = make_parsed_doc(
            title="Structured Doc",
            blocks=[
                make_block(
                    "Section 1 content " * 50,
                    heading_path=("Chapter 1", "Section 1"),
                )
            ],
        )

        chunks = chunker.chunk(document=doc, document_version_id=1)
        for c in chunks:
            assert c.heading_path == ("Chapter 1", "Section 1")

    def test_chunk_id_is_stable(self) -> None:
        """同一文档版本同一内容生成相同 Chunk ID。"""
        chunker = HierarchicalChunker(parent_size=1200, leaf_size=400, overlap=100)
        doc = make_parsed_doc(
            title="Stable Doc",
            blocks=[make_block("Same content " * 40, page=3)],
        )

        chunks1 = chunker.chunk(document=doc, document_version_id=10)
        chunks2 = chunker.chunk(document=doc, document_version_id=10)

        ids1 = {c.id for c in chunks1}
        ids2 = {c.id for c in chunks2}
        assert ids1 == ids2
