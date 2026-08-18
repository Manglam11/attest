import os

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.tools import retrieve_document_chunks

MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = (
    "You are Attest, a financial-document analyst. "
    "Answer questions using ONLY the indexed document. "
    "Call retrieve_document_chunks to fetch passages before answering. "
    "For a question with multiple parts, retrieve for each part. "
    "Cite the page numbers you used. "
    "If the document does not contain the answer, say: "
    "'I cannot answer this from the provided sources.'"
)

model = ChatGoogleGenerativeAI(
    model=MODEL,
    api_key=os.environ["GEMINI_API_KEY"],
)

agent = create_agent(
    model,
    tools=[retrieve_document_chunks],
    system_prompt=SYSTEM_PROMPT,
)


def run_agent(question: str):
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result
