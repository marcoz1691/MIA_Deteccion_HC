"""Índice FAISS para RAG sobre base de conocimiento clínica."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class RAGIndex:
    """Indexación y recuperación de chunks clínicos con FAISS + sentence-transformers."""

    def __init__(
        self,
        knowledge_dir: Path | str = "s7/knowledge",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_path: Path | str = "salidas_s7/faiss_index",
        top_k: int = 3,
    ):
        self.knowledge_dir = Path(knowledge_dir)
        self.embedding_model_name = embedding_model
        self.index_path = Path(index_path)
        self.top_k = top_k
        self._model = None
        self._index = None
        self._chunks: list[str] = []

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(
                    self.embedding_model_name, local_files_only=True
                )
            except Exception:
                self._model = SentenceTransformer(self.embedding_model_name)

    def _load_chunks(self) -> list[str]:
        chunks = []
        for f in sorted(self.knowledge_dir.glob("*.txt")):
            text = f.read_text(encoding="utf-8").strip()
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    chunks.append(para)
        return chunks

    def build(self) -> "RAGIndex":
        import faiss

        self._load_model()
        self._chunks = self._load_chunks()
        if not self._chunks:
            raise FileNotFoundError(f"No hay chunks en {self.knowledge_dir}")

        embeddings = self._model.encode(self._chunks, show_progress_bar=False)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

        self.index_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path / "index.faiss"))
        (self.index_path / "chunks.json").write_text(
            json.dumps(self._chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return self

    def load(self) -> "RAGIndex":
        import faiss

        self._load_model()
        idx_file = self.index_path / "index.faiss"
        chunks_file = self.index_path / "chunks.json"
        if not idx_file.exists() or not chunks_file.exists():
            return self.build()
        guardados = json.loads(chunks_file.read_text(encoding="utf-8"))
        actuales = self._load_chunks()
        if guardados != actuales:
            return self.build()
        self._index = faiss.read_index(str(idx_file))
        self._chunks = guardados
        return self

    def retrieve(self, query: str) -> str:
        """Retorna top-k chunks concatenados como contexto."""
        if self._index is None:
            self.load()
        self._load_model()
        q = self._model.encode([query], show_progress_bar=False)
        q = np.asarray(q, dtype=np.float32)
        import faiss
        faiss.normalize_L2(q)
        scores, indices = self._index.search(q, min(self.top_k, len(self._chunks)))
        parts = [self._chunks[i] for i in indices[0] if i >= 0]
        return "\n---\n".join(parts)
