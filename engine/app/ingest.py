import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

PDF_PATH = "/code/data/corpus/aapl_10k.pdf"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
VECTOR_SIZE = 384


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_text(text)


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    model = SentenceTransformer(EMBED_MODEL)
    vectors = model.encode(chunks, show_progress_bar=True)
    return vectors.tolist()


def store_vectors(chunks: list[str], vectors: list[list[float]]) -> None:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    points = [
        PointStruct(id=i, vector=vectors[i], payload={"text": chunks[i]})
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION, points=points)


if __name__ == "__main__":
    full_text = extract_text(PDF_PATH)
    chunks = chunk_text(full_text)
    vectors = embed_chunks(chunks)
    store_vectors(chunks, vectors)
    print(f"Stored {len(chunks)} points in collection '{COLLECTION}'.")