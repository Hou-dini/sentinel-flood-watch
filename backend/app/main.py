import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.memory import InMemoryMemoryService

# Import ADK primitives
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

# Import our agent, tools and database functions
from app.agent import root_agent
from app.app_utils.telemetry import setup_telemetry
from app.database import db_service, get_alerts, get_analytics_summary
from app.services import AgentService
from app.tools import STATIC_DIR, scan_zone_tool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Telemetry (Arize Phoenix & GCP Agent Engine)
    try:
        setup_telemetry()
        logging.info("Telemetry initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize telemetry: {e}")

    # Initialize the ADK memory and session services and the Runner object
    try:
        is_prod = os.environ.get("ENV") == "production" or "GOOGLE_CLOUD_PROJECT" in os.environ
        
        if is_prod:
            from google.adk.sessions import VertexAiSessionService
            from google.adk.memory import VertexAiMemoryBankService
            
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
            agent_engine_id = os.environ.get("AGENT_ENGINE_ID")

            if not agent_engine_id:
                logging.warning(
                    "AGENT_ENGINE_ID not set. VertexAiMemoryBankService requires it. "
                    "Set it to the numeric ID from your deployed Agent Engine."
                )

            session_service = VertexAiSessionService(
                project=project_id, location=location, agent_engine_id=agent_engine_id
            )
            memory_service = VertexAiMemoryBankService(
                project=project_id, location=location, agent_engine_id=agent_engine_id
            )
            logging.info("Initialized production Vertex AI Session and Memory services.")
        else:
            session_service = InMemorySessionService()
            memory_service = InMemoryMemoryService()
            logging.info("Initialized local in-memory Session and Memory services.")

        plugins = []
        model_armor_template = os.environ.get("MODEL_ARMOR_TEMPLATE")
        if model_armor_template:
            from app.app_utils.safety_plugin import ModelArmorSafetyPlugin
            plugins.append(ModelArmorSafetyPlugin(template_name=model_armor_template))
            logging.info("Model Armor safety plugin configured.")

        runner = Runner(
            agent=root_agent,
            app_name="sentinel",
            session_service=session_service,
            memory_service=memory_service,
            plugins=plugins,
        )
        app.state.runner = runner
        logging.info("ADK Runner and session services initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize ADK Runner: {e}")
        app.state.runner = None

    # Connect to the database proactively to check connection health at startup
    try:
        db_service.connect()
    except Exception as e:
        logging.error(f"Database connection error during startup: {e}")

    yield

    # Cleanup resources upon shutdown
    try:
        db_service.disconnect()
        logging.info("Database service disconnected successfully.")
    except Exception as e:
        logging.error(f"Error disconnecting database service on shutdown: {e}")


# FastAPI Setup
app = FastAPI(
    title="Sentinel Flood-Watch API",
    description="Agentic monitoring and alert API for Accra flood zones.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Setup for local dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def chat_stream(request: ChatRequest, fastapi_request: Request):
    """Streams the ADK AI Agent's reasoning, tool executions, and final replies using SSE."""
    session_id = request.session_id or "default_session"
    user_id = request.user_id or "default_user"
    runner = fastapi_request.app.state.runner
    agent_service = AgentService(runner)

    async def event_generator():
        try:
            async for chunk in agent_service.run_agent_task_stream(
                prompt=request.message, user_id=user_id, session_id=session_id
            ):
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
