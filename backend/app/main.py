import os

from dotenv import load_dotenv

load_dotenv()
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Import ADK primitives
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

# Import our agent, tools and database functions
from app.agent import root_agent
from app.app_utils.telemetry import setup_telemetry
from app.database import get_alerts, get_analytics_summary
from app.tools import STATIC_DIR, scan_zone_tool

# Initialize Telemetry (Arize Phoenix & GCP Agent Engine)
setup_telemetry()

# FastAPI Setup
app = FastAPI(
    title="Sentinel Flood-Watch API",
    description="Agentic monitoring and alert API for Accra flood zones.",
    version="1.0.0",
)

# CORS Setup for local dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Service
session_service = InMemorySessionService()

# Mount Static Files (serves PIL-generated mock images and evidence links)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount Frontend Dashboard
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
)
if os.path.exists(FRONTEND_DIR):
    app.mount(
        "/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="dashboard"
    )


# Request Models
class ScanRequest(BaseModel):
    latitude: float
    longitude: float
    site_name: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default_session"
    user_id: str | None = "default_user"


# Endpoints
@app.get("/api/v1/alerts")
async def fetch_alerts(query: str | None = None):
    """Retrieves logged alerts from the database."""
    try:
        alerts = await get_alerts(query)
        return {"status": "success", "count": len(alerts), "alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics")
async def fetch_analytics():
    """Retrieves live analytics (total alerts, scans processed, success rate)."""
    try:
        summary = await get_analytics_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scan-zone")
async def scan_zone(request: ScanRequest):
    """Directly triggers satellite scan for given coordinates."""
    try:
        result = await scan_zone_tool(
            latitude=request.latitude,
            longitude=request.longitude,
            site_name=request.site_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat")
async def chat_stream(request: ChatRequest):
    """Streams the ADK AI Agent's reasoning, tool executions, and final replies using SSE."""
    session_id = request.session_id or "default_session"
    user_id = request.user_id or "default_user"

    # Ensure session exists in the service
    session = await session_service.get_session(
        app_name="sentinel", user_id=user_id, session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name="sentinel", user_id=user_id, session_id=session_id
        )

    async def event_generator():
        try:
            runner = Runner(
                agent=root_agent, app_name="sentinel", session_service=session_service
            )
            new_msg = types.Content(
                role="user", parts=[types.Part.from_text(text=request.message)]
            )

            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=new_msg
            ):
                author = event.author
                text = ""
                if event.content and event.content.parts:
                    text = "".join([p.text for p in event.content.parts if p.text])

                # Check for tool/function calls
                func_calls = []
                for fc in event.get_function_calls():
                    func_calls.append(
                        {"name": fc.name, "args": dict(fc.args) if fc.args else {}}
                    )

                # Check for tool/function responses
                func_responses = []
                for fr in event.get_function_responses():
                    func_responses.append({"name": fr.name, "response": fr.response})

                chunk = {
                    "id": event.id,
                    "author": author,
                    "text": text,
                    "function_calls": func_calls,
                    "function_responses": func_responses,
                    "is_final": event.is_final_response(),
                }

                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            err_chunk = {
                "id": "error",
                "author": "system",
                "text": f"Error running agent: {e!s}",
                "is_final": True,
            }
            yield f"data: {json.dumps(err_chunk)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Root Endpoint
@app.get("/")
async def root():
    return {
        "app": "Sentinel Flood-Watch",
        "description": "Accra urban flooding satellite monitoring AI Agent API.",
        "status": "online",
    }
