import hashlib
import re

from policymind.documents.models import Chunk, ChunkContext, DocumentBlock, ParsedDocument


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
        context: ChunkContext,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []

        for block in document.blocks:
            block_chunks = self._chunk_block(block=block, context=context)
            chunks.extend(block_chunks)

        return chunks

    def _chunk_block(
        self,
        block: DocumentBlock,
        context: ChunkContext,
    ) -> list[Chunk]:
        text = block.text.strip()
        if not text:
            return []

        if block.block_type == "table":
            return self._chunk_table(block, context)

        parent_id = self._make_chunk_id(
            context.document_version_id,
            block.page_number,
            block.bbox,
            text,
            "parent",
        )
        parent = self._make_chunk(
            chunk_id=parent_id,
            parent_id=None,
            level="parent",
            text=text[: self.parent_size],
            block=block,
            context=context,
        )
        chunks: list[Chunk] = [parent]

        if len(text) <= self.leaf_size:
            leaf_id = self._make_chunk_id(
                context.document_version_id,
                block.page_number,
                block.bbox,
                text,
                "leaf",
            )
            chunks.append(
                self._make_chunk(
                    chunk_id=leaf_id,
                    parent_id=parent_id,
                    level="leaf",
                    text=text,
                    block=block,
                    context=context,
                )
            )
        else:
            step = self.leaf_size - self.overlap
            for start in range(0, len(text), step):
                leaf_text = text[start : start + self.leaf_size]
                if not leaf_text.strip():
                    continue
                leaf_id = self._make_chunk_id(
                    context.document_version_id,
                    block.page_number,
                    block.bbox,
                    leaf_text,
                    f"leaf-{start}",
                )
                chunks.append(
                    self._make_chunk(
                        chunk_id=leaf_id,
                        parent_id=parent_id,
                        level="leaf",
                        text=leaf_text,
                        block=block,
                        context=context,
                    )
                )

        return chunks

    def _chunk_table(
        self,
        block: DocumentBlock,
        context: ChunkContext,
    ) -> list[Chunk]:
        lines = block.text.strip().split("\n")
        if len(lines) < 3:
            return self._chunk_block(
                DocumentBlock(
                    text=block.text,
                    page_number=block.page_number,
                    block_type="text",
                    heading_path=block.heading_path,
                    bbox=block.bbox,
                ),
                context,
            )

        parent_id = self._make_chunk_id(
            context.document_version_id,
            block.page_number,
            block.bbox,
            block.text,
            "parent",
        )
        parent = self._make_chunk(
            chunk_id=parent_id,
            parent_id=None,
            level="parent",
            text=block.text[: self.parent_size],
            block=block,
            context=context,
        )
        chunks: list[Chunk] = [parent]

        batch_parts = [lines[0]]
        if len(lines) > 1:
            batch_parts.append(lines[1])
        if len(lines) > 2:
            batch_parts.append(lines[2])
        first_batch = "\n".join(batch_parts)

        leaf_id = self._make_chunk_id(
            context.document_version_id,
            block.page_number,
            block.bbox,
            first_batch,
            "leaf-0",
        )
        chunks.append(
            self._make_chunk(
                chunk_id=leaf_id,
                parent_id=parent_id,
                level="leaf",
                text=first_batch,
                block=block,
                context=context,
            )
        )

        return chunks

    @staticmethod
    def _make_chunk(
        chunk_id: str,
        parent_id: str | None,
        level: str,
        text: str,
        block: DocumentBlock,
        context: ChunkContext,
    ) -> Chunk:
        return Chunk(
            id=chunk_id,
            tenant_id=context.tenant_id,
            document_id=context.document_id,
            document_version_id=context.document_version_id,
            parent_id=parent_id,
            level=level,  # type: ignore[arg-type]
            text=text,
            page_number=block.page_number,
            heading_path=block.heading_path,
            bbox=block.bbox,
            access_level=context.access_level,
            effective_from=context.effective_from,
            effective_to=context.effective_to,
        )

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
