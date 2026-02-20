"""
FastAPI application — WebSocket chat endpoint + REST helpers.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import (
    ProteoAgent, TextDelta, ToolUse, ImageResult, AudioResult, StreamEnd,
)
from .tools import CACHE_DIR

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Proteosurf starting — cache dir: %s", CACHE_DIR)
    yield
    logger.info("Proteosurf shutting down")


app = FastAPI(
    title="Proteosurf",
    description="AI-powered structural biology assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# WebSocket chat
# ---------------------------------------------------------------------------

@app.websocket("/chat")
async def chat_ws(ws: WebSocket):
    await ws.accept()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        await ws.send_json({"type": "error", "text": "ANTHROPIC_API_KEY not configured"})
        await ws.close()
        return

    agent = ProteoAgent(api_key=api_key)

    try:
        while True:
            data = await ws.receive_json()
            user_msg = data.get("message", "")
            if not user_msg:
                continue

            if user_msg.strip().lower() == "/reset":
                agent.reset()
                await ws.send_json({"type": "system", "text": "Conversation reset."})
                continue

            async for event in agent.chat(user_msg):
                if isinstance(event, TextDelta):
                    await ws.send_json({"type": "text", "text": event.text})
                elif isinstance(event, ToolUse):
                    await ws.send_json({
                        "type": "tool",
                        "tool_name": event.tool_name,
                        "tool_input": event.tool_input,
                        "result": event.result,
                    })
                elif isinstance(event, ImageResult):
                    await ws.send_json({
                        "type": "image",
                        "base64": event.base64_png,
                        "caption": event.caption,
                    })
                elif isinstance(event, AudioResult):
                    await ws.send_json({
                        "type": "audio",
                        "base64": event.base64_mp3,
                        "caption": event.caption,
                    })
                elif isinstance(event, StreamEnd):
                    await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as exc:
        logger.exception("WebSocket error")
        try:
            await ws.send_json({"type": "error", "text": str(exc)})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# REST helpers
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "cache_dir": str(CACHE_DIR)}


@app.get("/api/pdb/{pdb_id}")
async def get_pdb(pdb_id: str):
    """Serve a cached PDB file for Mol* to load."""
    from .tools import download_pdb
    try:
        path = download_pdb(pdb_id)
        return FileResponse(path, media_type="chemical/x-pdb", filename=f"{pdb_id}.pdb")
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/api/narrate")
async def narrate(text: str):
    """Stream ElevenLabs TTS audio for real-time playback."""
    from .voice import narrate_streaming
    try:
        return StreamingResponse(
            narrate_streaming(text),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=narration.mp3"},
        )
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/api/sponsors")
async def sponsors():
    """List integrated sponsor tools and their status."""
    import shutil
    checks = {
        "claude_agent_sdk": _check_import("claude_agent_sdk"),
        "elevenlabs": _check_import("elevenlabs") and bool(os.environ.get("ELEVENLABS_API_KEY")),
        "databricks_mlflow": _check_import("mlflow"),
        "nemotron": bool(os.environ.get("NVIDIA_API_KEY")),
        "truemarket": bool(os.environ.get("TRUEMARKET_API_KEY")),
        "nia_nozomio": bool(os.environ.get("NIA_API_KEY")) or _check_import("nia_py"),
    }
    return {"sponsors": checks}


def _check_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Static frontend (production)
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")
