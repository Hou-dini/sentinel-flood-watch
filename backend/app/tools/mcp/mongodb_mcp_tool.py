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

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# On production (e.g. Cloud Run / Linux container), we run the globally installed
# mongodb-mcp-server binary directly to avoid npm registry downloads/caching latency.
# On Windows / local development, we fallback to npx.
is_production = os.environ.get("GOOGLE_CLOUD_PROJECT") is not None or os.name != "nt"

command = "mongodb-mcp-server" if is_production else "npx"
args = [] if is_production else ["-y", "@mongodb-js/mongodb-mcp-server"]

# Configure MongoDB MCP Toolset
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
        )
    )
)
