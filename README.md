# Attest

A multimodal, self-grading RAG system for financial documents.

Ask real financial reports (10-Ks, 10-Qs, annual reports) plain-English
questions and get answers that **cite their sources**, **read the charts
inside the document** (not just the text), and **grade their own
faithfulness** — flagging any answer that cannot be grounded.

## Architecture

Two clean halves:

- **Django** — product shell (auth, roles, pages, history, the UI a user touches)
- **FastAPI** — the RAG + agent engine (retrieve, read charts, self-grade)
- **PostgreSQL** — users, metadata, eval scores, history
- **Qdrant** — vector store (embeddings of text + figure descriptions)

## Status

Turn 0 — ground setup. Environment live (WSL2 · Docker · repo).
Build follows a 7-turn spiral; Turn 1 is the walking skeleton (text RAG, end to end).

## Stack

Django · FastAPI · PostgreSQL · Qdrant · LangChain / LangGraph · RAGAS ·
PyMuPDF · Docker Compose

---
*Author: Manglam Dubey*