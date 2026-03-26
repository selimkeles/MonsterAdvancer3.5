"""FastAPI application entry point for Monster Advancer API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import monsters

app = FastAPI(
    title="D&D 3.5 Monster Advancer API",
    description="REST API for advancing D&D 3.5 monsters with HD, size changes, feats, and class levels.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"null|file://.*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monsters.router, prefix="/api", tags=["monsters"])


@app.get("/")
def root():
    return {"message": "D&D 3.5 Monster Advancer API", "version": "1.0.0"}
