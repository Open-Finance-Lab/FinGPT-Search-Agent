import uvicorn
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP("My MCP Server")

@mcp.tool()
def greet(name: str) -> str:
    return f"Hello, {name}!"

# 2) Create the ASGI application for Streamable HTTP transport
#    This provides both JSON-RPC and streaming endpoints under /mcp
stream_app = mcp.streamable_http_app()

# 3) Wrap with CORS so browsers can connect from any origin
app = CORSMiddleware(
    stream_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],  # so client can read the session header
)

# 4) Run with Uvicorn instead of mcp.run() for CORS to work, in theory
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="debug")
