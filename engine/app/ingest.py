import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseVector,
    Modifier,
    PointStruct,
)

PDF_PATH = "/code/data/corpus/aapl_10k.pdf"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
COLLECTION = "attest_chunks"
VECTOR_SIZE = 384
DENSE_NAME = "dense"
SPARSE_NAME = "sparse"


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


def embed_chunks_sparse(chunks: list[str]) -> list[SparseVector]:
    model = SparseTextEmbedding(SPARSE_MODEL)
    embeddings = model.embed(chunks)
    return [
        SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
        for e in embeddings
    ]


def store_vectors(
    chunks: list[str],
    dense_vectors: list[list[float]],
    sparse_vectors: list[SparseVector],
) -> None:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            DENSE_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            SPARSE_NAME: SparseVectorParams(modifier=Modifier.IDF),
        },
    )
    points = [
        PointStruct(
            id=i,
            vector={DENSE_NAME: dense_vectors[i], SPARSE_NAME: sparse_vectors[i]},
            payload={"text": chunks[i]},
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION, points=points)


if __name__ == "__main__":
    full_text = extract_text(PDF_PATH)
    chunks = chunk_text(full_text)
    dense_vectors = embed_chunks(chunks)
    sparse_vectors = embed_chunks_sparse(chunks)
    store_vectors(chunks, dense_vectors, sparse_vectors)