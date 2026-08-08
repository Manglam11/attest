from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
TOP_K = 5


def embed_question(question: str) -> list[float]:
    model = SentenceTransformer(EMBED_MODEL)
    vector = model.encode(question)
    return vector.tolist()


def search(vector: list[float], top_k: int = TOP_K) -> list[str]:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    hits = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=top_k,
    ).points
    return [hit.payload["text"] for hit in hits]


def retrieve(question: str, top_k: int = TOP_K) -> list[str]:
    vector = embed_question(question)
    return search(vector, top_k)


if __name__ == "__main__":
    question = "What was Apple's total net sales?"
    chunks = retrieve(question)
    print(f"Retrieved {len(chunks)} chunks for: {question!r}\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"--- chunk {i} ---")
        print(chunk[:300])
        print()