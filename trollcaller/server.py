"""FastAPI server with Twilio webhook and WebSocket endpoints."""

import logging
import random

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response

from .media_stream import MediaStreamHandler
from .prompts import PERSONAS, SPAMMERS, DEFAULT_PERSONA
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TrollCaller", description="Voice-cloned spam-callback bot")


@app.get("/")
async def root():
    return {
        "name": "TrollCaller",
        "status": "ready",
        "troller_personas": list(PERSONAS.keys()),
        "spammer_personas": list(SPAMMERS.keys()),
    }


@app.post("/incoming-call")
async def incoming_call(request: Request):
    """Twilio webhook for incoming calls.

    Returns TwiML that connects the call to our WebSocket Media Stream.
    """
    # Pick a random persona for fun (or use query param)
    form = await request.form()
    caller = form.get("From", "Unknown")
    logger.info(f"Incoming call from {caller}")

    # Determine WebSocket URL
    host = request.headers.get("host", f"localhost:{settings.port}")
    scheme = "wss" if request.url.scheme == "https" else "ws"
    ws_url = f"{scheme}://{host}/media-stream"

    # Pick persona (can be overridden via query param)
    persona = request.query_params.get("persona", DEFAULT_PERSONA)
    if persona not in PERSONAS:
        persona = DEFAULT_PERSONA

    # Return TwiML to start a Media Stream
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}?persona={persona}">
            <Parameter name="persona" value="{persona}" />
        </Stream>
    </Connect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams."""
    persona = websocket.query_params.get("persona", DEFAULT_PERSONA)
    handler = MediaStreamHandler(websocket, persona=persona)
    await handler.handle()


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    """Run the server."""
    import uvicorn

    logger.info(f"Starting TrollCaller on {settings.host}:{settings.port}")
    uvicorn.run(
        "trollcaller.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
