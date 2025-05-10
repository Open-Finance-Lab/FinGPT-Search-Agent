# backend/datascraper/mcp/mcp_tools.py
from django_mcp import mcp_app


# "hello_world" tool:
@mcp_app.tool(name="hello_world")
def hello_world_tool(params: dict = None):
    """
    Sample MCP tool that returns a greeting.

    MCP tools generally expect a dict of params. Here, we'll allow an optional 'name'.
    """
    if params is None:
        params = {}
    name = params.get('name', 'World')
    return f"Hello, {name}!"
