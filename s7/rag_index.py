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
        self._chunks: list[dict[str, str]] = []

    @staticmethod
    def _normalize_chunk(item: str | dict) -> dict[str, str]:
        if isinstance(item, str):
            return {"text": item, "fuente": "desconocida"}
        return {
            "text": str(item.get("text", "")),
            "fuente": str(item.get("fuente", "desconocida")),
        }

    def _normalize_chunks(self, raw: list) -> list[dict[str, str]]:
        return [self._normalize_chunk(item) for item in raw]

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(
                    self.embedding_model_name, local_files_only=True
                )
            except Exception:
                self._model = SentenceTransformer(self.embedding_model_name)

    def _load_chunks(self) -> list[dict[str, str]]:
        chunks: list[dict[str, str]] = []
        for f in sorted(self.knowledge_dir.glob("*.txt")):
            text = f.read_text(encoding="utf-8").strip()
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    chunks.append({"text": para, "fuente": f.name})
        return chunks

    def build(self) -> "RAGIndex":
        import faiss

        self._load_model()
        self._chunks = self._load_chunks()
        if not self._chunks:
            raise FileNotFoundError(f"No hay chunks en {self.knowledge_dir}")

        texts = [c["text"] for c in self._chunks]
        embeddings = self._model.encode(texts, show_progress_bar=False)
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
        guardados = self._normalize_chunks(json.loads(chunks_file.read_text(encoding="utf-8")))
        actuales = self._load_chunks()
        if guardados != actuales:
            return self.build()
        self._index = faiss.read_index(str(idx_file))
        self._chunks = guardados
        return self

    def retrieve_hits(self, query: str) -> list[dict[str, str | float]]:
        """Retorna top-k chunks con metadatos de fuente y score de similitud."""
        if self._index is None:
            self.load()
        self._load_model()
        q = self._model.encode([query], show_progress_bar=False)
        q = np.asarray(q, dtype=np.float32)
        import faiss

        faiss.normalize_L2(q)
        k = min(self.top_k, len(self._chunks))
        scores, indices = self._index.search(q, k)
        hits: list[dict[str, str | float]] = []
        for rank, idx in enumerate(indices[0]):
            if idx < 0:
                continue
            chunk = self._chunks[idx]
            hits.append(
                {
                    "fuente": chunk["fuente"],
                    "extracto": chunk["text"],
                    "score": float(scores[0][rank]),
                }
            )
        return hits

    def retrieve(self, query: str) -> str:
        """Retorna top-k chunks concatenados como contexto."""
        hits = self.retrieve_hits(query)
        return "\n---\n".join(str(h["extracto"]) for h in hits)
