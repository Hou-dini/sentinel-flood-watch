import os
import pytest
from dotenv import load_dotenv

# Load environment variables from backend/.env or root .env
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
)

# Restrict MongoDB connection pool size globally to avoid exceeding Atlas M0 limits
mongodb_uri = os.environ.get("MONGODB_URI", "")
if mongodb_uri:
    max_pool_size = os.environ.get("MONGODB_MAX_POOL_SIZE", "5")
    if "maxPoolSize=" not in mongodb_uri:
        separator = "&" if "?" in mongodb_uri else "?"
        mongodb_uri = f"{mongodb_uri}{separator}maxPoolSize={max_pool_size}"
        os.environ["MONGODB_URI"] = mongodb_uri

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def cleanup_mcp_sessions():
    yield
    try:
        from app.tools.mcp.mongodb_mcp_tool import mongodb_mcp_tool
        await mongodb_mcp_tool._mcp_session_manager.close()
    except Exception:
        pass
