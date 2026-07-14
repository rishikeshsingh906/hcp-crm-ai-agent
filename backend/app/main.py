from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import interactions, chat, hcp

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First HCP CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hcp.router)
app.include_router(interactions.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
