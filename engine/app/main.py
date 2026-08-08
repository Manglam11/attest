from fastapi import FastAPI

app = FastAPI(title="Attest Engine")


@app.get("/health")
def health():
    return {"status": "alive", "service": "engine"}