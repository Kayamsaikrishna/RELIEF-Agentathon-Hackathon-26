"""Rule base and search.

Rules are short paraphrases of official documents, each with source, section, date, link and the
exact quote it rests on. Search uses ChromaDB with an embedding model chosen by RELIEF_EMBEDDER:
  ollama   nomic-embed-text served by the local Ollama (no extra download)
  bge      BAAI/bge-small-en-v1.5 via sentence-transformers (install with `pip install .[bge]`)
  hashing  deterministic hashed n-grams (offline, lower quality; used in tests)
A rule can always be fetched by id without any embedding, and the verifier relies on that.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Protocol

from relief.config import Settings, get_settings
from relief.contracts.schemas import RulePassage

log = logging.getLogger(__name__)
BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbedder:
    name = "hashing-512"

    def __init__(self, n_features: int = 512):
        from sklearn.feature_extraction.text import HashingVectorizer

        self._vec = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2",
                                      ngram_range=(1, 2), stop_words="english", lowercase=True)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        return self._vec.transform(texts).toarray().tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]


class BgeEmbedder:
    name = "bge-small-en-v1.5"

    def __init__(self, model_name: str = BGE_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "RELIEF_EMBEDDER=bge needs sentence-transformers. Run: pip install '.[bge]' "
                "(or set RELIEF_EMBEDDER=hashing for an offline, lower-quality search)."
            ) from exc
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([BGE_QUERY_PREFIX + text], normalize_embeddings=True)[0].tolist()


class OllamaEmbedder:
    """Embeddings from a model served by the local Ollama (default nomic-embed-text). No extra download or Python package."""

    def __init__(self, model: str, host: str, timeout: float = 120.0):
        import ollama

        self.model = model
        self.name = f"ollama-{model.split(':')[0].replace('/', '_')}"
        self._client = ollama.Client(host=host, timeout=timeout)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = self._client.embed(model=self.model, input=texts)
        except Exception as exc:
            raise RuntimeError(f"Embedding model '{self.model}' is not available from Ollama: {exc}. "
                               f"Run: ollama pull {self.model}") from exc
        vecs = resp["embeddings"] if isinstance(resp, dict) else resp.embeddings
        return [list(v) for v in vecs]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(["search_document: " + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed(["search_query: " + text])[0]


def make_embedder(kind: str, settings: Optional[Settings] = None) -> Embedder:
    if kind == "hashing":
        return HashingEmbedder()
    if kind == "bge":
        return BgeEmbedder()
    if kind == "ollama":
        s = settings or get_settings()
        return OllamaEmbedder(s.embed_model, s.llm_host)
    raise ValueError(f"Unknown RELIEF_EMBEDDER '{kind}' (use ollama, bge or hashing)")


class RulesKB:
    def __init__(self, settings: Optional[Settings] = None, embedder: Optional[Embedder] = None,
                 persist_dir: Optional[Path] = None):
        self.settings = settings or get_settings()
        rules_dir = self.settings.rules_dir
        sources = {s["source_id"]: s for s in json.loads((rules_dir / "sources.json").read_text(encoding="utf-8"))}
        raw = json.loads((rules_dir / "rules.json").read_text(encoding="utf-8"))
        checked: dict[str, bool] = {}
        vfile = rules_dir / "verification.json"
        if vfile.exists():
            checked = json.loads(vfile.read_text(encoding="utf-8"))
        self._rules: dict[str, RulePassage] = {}
        self._applies: dict[str, list[str]] = {}
        for r in raw:
            s = sources[r["source_id"]]
            self._rules[r["rule_id"]] = RulePassage(
                rule_id=r["rule_id"], source_id=r["source_id"], source_title=s["title"], issuer=s["issuer"],
                date=s["date"], url=s["url"], section=r["section"], page=r.get("page") or None,
                quote=r.get("quote", ""), text=r["text"], quote_checked=bool(checked.get(r["rule_id"], False)),
            )
            self._applies[r["rule_id"]] = r.get("applies_to", [])
        self._embedder = embedder
        self._persist_dir = persist_dir or self.settings.chroma_dir
        self._collection = None

    # ------------------------------------------------------------ direct lookup
    def get(self, rule_id: str) -> Optional[RulePassage]:
        return self._rules.get(rule_id)

    def get_many(self, ids: list[str]) -> list[RulePassage]:
        return [self._rules[i] for i in dict.fromkeys(ids) if i in self._rules]

    def all(self) -> list[RulePassage]:
        return list(self._rules.values())

    def ids(self) -> set[str]:
        return set(self._rules)

    def for_blocker(self, blocker: str) -> list[RulePassage]:
        return [self._rules[i] for i, a in self._applies.items() if blocker in a]

    # ------------------------------------------------------------ semantic search
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = make_embedder(self.settings.embedder, self.settings)
        return self._embedder

    def _content_hash(self) -> str:
        h = hashlib.sha256()
        for r in sorted(self._rules.values(), key=lambda x: x.rule_id):
            h.update(f"{r.rule_id}|{r.section}|{r.text}".encode("utf-8"))
        return h.hexdigest()[:16]

    def _doc_text(self, r: RulePassage) -> str:
        return f"{r.source_title}. {r.section}. {r.text}"

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb

        self._persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self._persist_dir))
        digest = self._content_hash()
        cname = f"rules_{self.embedder.name.replace('.', '_').replace('-', '_')}"
        col = client.get_or_create_collection(name=cname, metadata={"hnsw:space": "cosine", "digest": digest})
        if col.metadata.get("digest") != digest or col.count() != len(self._rules):
            client.delete_collection(cname)
            col = client.create_collection(name=cname, metadata={"hnsw:space": "cosine", "digest": digest})
            rules = list(self._rules.values())
            col.add(ids=[r.rule_id for r in rules],
                    documents=[self._doc_text(r) for r in rules],
                    embeddings=self.embedder.embed_documents([self._doc_text(r) for r in rules]))
        self._collection = col
        return col

    def search(self, query: str, k: int = 3, blocker: Optional[str] = None) -> list[RulePassage]:
        if not query.strip():
            return []
        col = self._ensure_collection()
        n = min(len(self._rules), max(k * 4, k) if blocker else k)
        res = col.query(query_embeddings=[self.embedder.embed_query(query)], n_results=n)
        out: list[RulePassage] = []
        for rid, dist in zip(res["ids"][0], res["distances"][0]):
            if blocker and blocker not in self._applies.get(rid, []):
                continue
            p = self._rules[rid].model_copy(update={"score": round(1.0 - float(dist), 4)})
            out.append(p)
            if len(out) == k:
                break
        return out
