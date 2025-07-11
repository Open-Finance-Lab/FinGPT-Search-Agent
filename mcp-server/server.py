import uvicorn
# from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(title="Echo MCP Server with CORS")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["GET", "POST"],
#     allow_headers=["*"],
#     expose_headers=["Mcp-Session-Id"],  # so client can read the session header
# )

mcp = FastMCP(
    name="FinGPT MCP Server",
    port=9000
)

@mcp.tool()
def greet(name: str) -> str:
    print(f"[DEBUG] greet tool called with name: {name}")
    result = f"Hello, {name}!"
    print(f"[DEBUG] greet tool returning: {result}")
    return result

if __name__ == "__main__":
    # uvicorn.run(app, host="127.0.0.1", port=9000, log_level="debug")
    mcp.run(transport="sse")
