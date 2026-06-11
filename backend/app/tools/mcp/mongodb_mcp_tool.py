# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from dotenv import load_dotenv

load_dotenv()

# Restrict MongoDB connection pool size globally to avoid exceeding Atlas M0 limits
mongodb_uri = os.environ.get("MONGODB_URI", "")
if mongodb_uri:
    max_pool_size = os.environ.get("MONGODB_MAX_POOL_SIZE", "5")
    if "maxPoolSize=" not in mongodb_uri:
        separator = "&" if "?" in mongodb_uri else "?"
        mongodb_uri = f"{mongodb_uri}{separator}maxPoolSize={max_pool_size}"
        os.environ["MONGODB_URI"] = mongodb_uri

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# On Windows / local development, we fallback to npx.
is_production = os.name != "nt"

command = "mongodb-mcp-server" if is_production else "npx"
args = [] if is_production else ["-y", "mongodb-mcp-server"]

# Configure MongoDB MCP Toolset
# Only expose the tools the agent needs: find (query alerts) and insert-many (log alerts).
# The 'connect' tool is called internally by the auto-connect callback and does not need to be exposed.
mongodb_mcp_tool = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=command,
            args=args,
            env={
                **os.environ,
                "MONGODB_URI": os.environ.get("MONGODB_URI", ""),
                "MDB_MCP_CONNECTION_STRING": os.environ.get("MONGODB_URI", ""),
            },
        ),
        timeout=90.0,
    ),
    tool_name_prefix="mongodb",
    tool_filter=["find", "insert-many"],
)
