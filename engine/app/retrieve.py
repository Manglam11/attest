from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Prefetch,
    SparseVector,
    FusionQuery,
    Fusion,
    NamedVector,
    Filter,
    FieldCondition,
    MatchValue,
)

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
RERANK_MODEL = "BAAI/bge-reranker-base"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "sparse"
TOP_K = 5
PREFETCH = 20
RERANK_POOL = 20

_dense_model = SentenceTransformer(EMBED_MODEL)
_sparse_model = SparseTextEmbedding(SPARSE_MODEL)
_rerank_model = CrossEncoder(RERANK_MODEL)
_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def embed_question_dense(question: str) -> list[float]:
    vector = _dense_model.encode(question)
    return vector.tolist()


def embed_question_sparse(question: str) -> SparseVector:
    e = next(_sparse_model.embed([question]))
    return SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


def rerank(question: str, candidates: list[dict], top_k: int) -> list[dict]:
    if not candidates:
        return []
    pairs = [(question, c["text"]) for c in candidates]
    scores = _rerank_model.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [{**c, "score": float(score)} for c, score in ranked[:top_k]]


def owner_filter(owner_id: str, doc_id: str | None = None) -> Filter:
    # owner_id is always required and always comes from the verified token,
    # never from the caller — doc_id, if given, narrows within that owner's
    # own corpus, it can never widen past it.
    conditions = [FieldCondition(key="owner_id", match=MatchValue(value=owner_id))]
    if doc_id is not None:
        conditions.append(FieldCondition(key="doc_id", match=MatchValue(value=doc_id)))
    return Filter(must=conditions)


def search(
    question: str, owner_id: str, doc_id: str | None = None, top_k: int = TOP_K
) -> list[dict]:
    dense = embed_question_dense(question)
    sparse = embed_question_sparse(question)
    query_filter = owner_filter(owner_id, doc_id)
    hits = _client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_NAME, limit=PREFETCH, filter=query_filter),
            Prefetch(query=sparse, using=SPARSE_NAME, limit=PREFETCH, filter=query_filter),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        query_filter=query_filter,
        limit=RERANK_POOL,
    ).points
    candidates = [
        {
            "text": hit.payload["text"],
            "page": hit.payload["page"],
            "doc_id": hit.payload["doc_id"],
            "owner_id": hit.payload["owner_id"],
        }
        for hit in hits
    ]
    return rerank(question, candidates, top_k)


def retrieve(
    question: str, owner_id: str, doc_id: str | None = None, top_k: int = TOP_K
) -> list[dict]:
    return search(question, owner_id, doc_id, top_k)


if __name__ == "__main__":
    question = "How much did Apple spend on research and development?"
    chunks = retrieve(question, "alice")
    print(f"Retrieved {len(chunks)} chunks for: {question!r}\n")
    for i, chunk in enumerate(chunks, 1):
        marker = "  <-- 31,370 HERE" if "31,370" in chunk["text"] else ""
        print(f"--- chunk {i} · page {chunk['page']} ---{marker}")
        print(chunk["text"][:300])
        print()