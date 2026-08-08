from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, SparseVector, FusionQuery, Fusion, NamedVector

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "sparse"
TOP_K = 5
PREFETCH = 20


def embed_question_dense(question: str) -> list[float]:
    model = SentenceTransformer(EMBED_MODEL)
    vector = model.encode(question)
    return vector.tolist()


def embed_question_sparse(question: str) -> SparseVector:
    model = SparseTextEmbedding(SPARSE_MODEL)
    e = next(model.embed([question]))
    return SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


def search(question: str, top_k: int = TOP_K) -> list[str]:
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
        limit=top_k,
    ).points
    return [hit.payload["text"] for hit in hits]


def retrieve(question: str, top_k: int = TOP_K) -> list[str]:
    return search(question, top_k)


if __name__ == "__main__":
    question = "What was Apple's total net sales?"
    chunks = retrieve(question)
    print(f"Retrieved {len(chunks)} chunks for: {question!r}\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- chunk {i} ---")
        print(chunk[:300])
        print()