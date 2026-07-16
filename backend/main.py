"""FastAPI application for the Cairn backend."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cairn.agents.agent import run_turn
from cairn.agents.model import get_model
from cairn.registry import (
	get_active_attendee,
	get_store,
	get_faq_retriever,
	get_attendee_retriever,
	get_session_retriever,
	me_payload)

@asynccontextmanager
async def lifespan(app: FastAPI):
	# initialize data store at boot
	get_active_attendee()
	get_faq_retriever()
	get_attendee_retriever()
	get_session_retriever()
	get_store()
	get_model()
	yield

app = FastAPI(title="Cairn", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
	allow_methods = ["*"],
	allow_headers = ["*"]
)

class ChatTurn(BaseModel):
	role: str
	content: str

class ChatRequest(BaseModel):
	message: str
	history: list[ChatTurn] = []

@app.get("/api/health")
def health():
	return {
		"status": "ok",
		"vertex_enabled": get_model() is not None
	}

@app.get("/api/me")
def me():
	return me_payload()

@app.post("/api/chat")
def chat(req: ChatRequest):
	return run_turn(req.message, history=[t.model_dump() for t in req.history])
