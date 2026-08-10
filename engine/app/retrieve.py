from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, SparseVector, FusionQuery, Fusion, NamedVector
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "sparse"
TOP_K = 5
PREFETCH = 20
RERANK_POOL = 20
def embed_question_dense(question: str) -> list[float]:
    model = SentenceTransformer(EMBED_MODEL)
    vector = model.encode(question)
    return vector.tolist()
def embed_question_sparse(question: str) -> SparseVector:
    model = SparseTextEmbedding(SPARSE_MODEL)
    e = next(model.embed([question]))
    return SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
def rerank(question: str, candidates: list[dict], top_k: int) -> list[dict]:
    model = CrossEncoder(RERANK_MODEL)
    pairs = [(question, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]
def search(question: str, top_k: int = TOP_K) -> list[dict]:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    dense = embed_question_dense(question)
    sparse = embed_question_sparse(question)
    hits = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_NAME, limit=PREFETCH),
            Prefetch(query=sparse, using=SPARSE_NAME, limit=PREFETCH),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RERANK_POOL,
    ).points
    candidates = [{"text": hit.payload["text"], "page": hit.payload["page"]} for hit in hits]
    return rerank(question, candidates, top_k)
def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    return search(question, top_k)
if __name__ == "__main__":
    question = "How much did Apple spend on research and development?"
    chunks = retrieve(question)
    print(f"Retrieved {len(chunks)} chunks for: {question!r}\n")
    for i, chunk in enumerate(chunks, 1):
        marker = "  <-- 31,370 HERE" if "31,370" in chunk["text"] else ""
        print(f"--- chunk {i} · page {chunk['page']} ---{marker}")
        print(chunk["text"][:300])
        print()