import hashlib
import re

from policymind.documents.models import Chunk, DocumentBlock, ParsedDocument


class HierarchicalChunker:
    def __init__(
        self,
        parent_size: int = 1200,
        leaf_size: int = 400,
        overlap: int = 100,
    ) -> None:
        self.parent_size = parent_size
        self.leaf_size = leaf_size
        self.overlap = overlap

    def chunk(
        self,
        document: ParsedDocument,
        document_version_id: int,
        tenant_id: int = 1,
        document_id: int = 0,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []

        for block in document.blocks:
            block_chunks = self._chunk_block(
                block=block,
                document_version_id=document_version_id,
                tenant_id=tenant_id,
                document_id=document_id,
            )
            chunks.extend(block_chunks)

        return chunks

    def _chunk_block(
        self,
        block: DocumentBlock,
        document_version_id: int,
        tenant_id: int,
        document_id: int,
    ) -> list[Chunk]:
        text = block.text.strip()
        if not text:
            return []

        # 表格不分块——整个表格作为一个 parent 和可能多个 leaf
        if block.block_type == "table":
            return self._chunk_table(
                block, document_version_id, tenant_id, document_id
            )

        # 生成 parent chunk
        parent_id = self._make_chunk_id(
            document_version_id, block.page_number, block.bbox, text, "parent"
        )
        parent = Chunk(
            id=parent_id,
            tenant_id=tenant_id,
            document_id=document_id,
            document_version_id=document_version_id,
            parent_id=None,
            level="parent",
            text=text[: self.parent_size],
            page_number=block.page_number,
            heading_path=block.heading_path,
            bbox=block.bbox,
        )
        chunks: list[Chunk] = [parent]

        # 分割为 leaf chunks
        if len(text) <= self.leaf_size:
            leaf_id = self._make_chunk_id(
                document_version_id,
                block.page_number,
                block.bbox,
                text,
                "leaf",
            )
            chunks.append(
                Chunk(
                    id=leaf_id,
                    tenant_id=tenant_id,
                    document_id=document_id,
                    document_version_id=document_version_id,
                    parent_id=parent_id,
                    level="leaf",
                    text=text,
                    page_number=block.page_number,
                    heading_path=block.heading_path,
                    bbox=block.bbox,
                )
            )
        else:
            step = self.leaf_size - self.overlap
            for start in range(0, len(text), step):
                leaf_text = text[start : start + self.leaf_size]
                if not leaf_text.strip():
                    continue
                leaf_id = self._make_chunk_id(
                    document_version_id,
                    block.page_number,
                    block.bbox,
                    leaf_text,
                    f"leaf-{start}",
                )
                chunks.append(
                    Chunk(
                        id=leaf_id,
                        tenant_id=tenant_id,
                        document_id=document_id,
                        document_version_id=document_version_id,
                        parent_id=parent_id,
                        level="leaf",
                        text=leaf_text,
                        page_number=block.page_number,
                        heading_path=block.heading_path,
                        bbox=block.bbox,
                    )
                )

        return chunks

    def _chunk_table(
        self,
        block: DocumentBlock,
        document_version_id: int,
        tenant_id: int,
        document_id: int,
    ) -> list[Chunk]:
        """表格：header + 前几行作为一个 chunk，后续行按需分割。"""
        lines = block.text.strip().split("\n")
        if len(lines) < 3:
            # 太小，当作普通文本
            return self._chunk_block(
                DocumentBlock(
                    text=block.text,
                    page_number=block.page_number,
                    block_type="text",
                    heading_path=block.heading_path,
                    bbox=block.bbox,
                ),
                document_version_id,
                tenant_id,
                document_id,
            )

        parent_id = self._make_chunk_id(
            document_version_id, block.page_number, block.bbox, block.text, "parent"
        )
        parent = Chunk(
            id=parent_id,
            tenant_id=tenant_id,
            document_id=document_id,
            document_version_id=document_version_id,
            parent_id=None,
            level="parent",
            text=block.text[: self.parent_size],
            page_number=block.page_number,
            heading_path=block.heading_path,
            bbox=block.bbox,
        )
        chunks: list[Chunk] = [parent]

        # Header + 前两行数据组成第一个 leaf
        batch_parts = [lines[0]]
        if len(lines) > 1:
            batch_parts.append(lines[1])
        if len(lines) > 2:
            batch_parts.append(lines[2])
        first_batch = "\n".join(batch_parts)
        leaf_id = self._make_chunk_id(
            document_version_id, block.page_number, block.bbox, first_batch, "leaf-0"
        )
        chunks.append(
            Chunk(
                id=leaf_id,
                tenant_id=tenant_id,
                document_id=document_id,
                document_version_id=document_version_id,
                parent_id=parent_id,
                level="leaf",
                text=first_batch,
                page_number=block.page_number,
                heading_path=block.heading_path,
                bbox=block.bbox,
            )
        )

        return chunks

    @staticmethod
    def _make_chunk_id(
        document_version_id: int,
        page: int,
        bbox: tuple[float, float, float, float] | None,
        text: str,
        suffix: str,
    ) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        raw = f"{document_version_id}|{page}|{bbox or ''}|{normalized}|{suffix}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
