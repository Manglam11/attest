import os
import fitz
from google import genai
from google.genai import types
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
FIGURE_MIN_PX = 200
VISION_MODEL = "gemini-3.6-flash"


def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    doc = fitz.open(pdf_path)
    pages = [(i + 1, page.get_text()) for i, page in enumerate(doc)]
    doc.close()
    return pages


def chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    records = []
    for page_num, page_text in pages:
        for chunk in splitter.split_text(page_text):
            records.append({"text": chunk, "page": page_num, "kind": "text"})
    return records


def extract_and_describe_figures(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = (
        "Describe this figure from a financial 10-K filing in detail. "
        "Include the chart type, what it measures, the axes, every "
        "company/index plotted, and any specific values or endpoints "
        "you can read. Be precise and factual."
    )
    records = []
    for i, page in enumerate(doc):
        page_num = i + 1
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.width < FIGURE_MIN_PX or pix.height < FIGURE_MIN_PX:
                continue
            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            png_bytes = pix.tobytes("png")
            resp = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                    prompt,
                ],
            )
            description = f"Figure on page {page_num}: {resp.text}"
            records.append({"text": description, "page": page_num, "kind": "figure"})
    doc.close()
    return records


def embed_chunks(texts: list[str]) -> list[list[float]]:
    model = SentenceTransformer(EMBED_MODEL)
    vectors = model.encode(texts, show_progress_bar=True)
    return vectors.tolist()


def embed_chunks_sparse(texts: list[str]) -> list[SparseVector]:
    model = SparseTextEmbedding(SPARSE_MODEL)
    embeddings = model.embed(texts)
    return [
        SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
        for e in embeddings
    ]


def store_vectors(
    records: list[dict],
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
            payload={"text": records[i]["text"], "page": records[i]["page"], "kind": records[i]["kind"]},
        )
        for i in range(len(records))
    ]
    client.upsert(collection_name=COLLECTION, points=points)


if __name__ == "__main__":
    pages = extract_pages(PDF_PATH)
    records = chunk_pages(pages)
    records += extract_and_describe_figures(PDF_PATH)
    texts = [r["text"] for r in records]
    dense_vectors = embed_chunks(texts)
    sparse_vectors = embed_chunks_sparse(texts)
    store_vectors(records, dense_vectors, sparse_vectors)
    print(f"Ingested {len(records)} records ({sum(r['kind']=='figure' for r in records)} figures).")