"""
simple mcp server loader - supports cursor-style mcp configs
loads external mcp servers from mcp_servers.json
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from agents import function_tool

logger = logging.getLogger(__name__)

# store active mcp clients
_active_clients: Dict[str, Any] = {}


def load_mcp_servers(config_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    load enabled mcp servers from config file
    supports cursor-style configuration with command/url/headers/env
    
    returns list of enabled server configs
    """
    if config_path is None:
        config_path = Path(__file__).parent / "mcp_servers.json"
    
    if not config_path.exists():
        logger.info(f"no mcp servers config found at {config_path}")
        return []
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        servers = config.get("mcpServers", {})
        enabled_servers = []
        
        for name, server_config in servers.items():
            if server_config.get("enabled", False):
                enabled_servers.append({
                    "name": name,
                    **server_config
                })
                logger.info(f"loaded mcp server: {name}")
        
        logger.info(f"total enabled mcp servers: {len(enabled_servers)}")
        return enabled_servers
    
    except Exception as e:
        logger.error(f"error loading mcp servers: {e}")
        return []


async def connect_mcp_server(server_config: Dict[str, Any]) -> Optional[Any]:
    """
    connect to an mcp server based on config
    
    args:
        server_config: server configuration with type/url/command
    
    returns:
        mcp client session or None if connection fails
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        server_name = server_config.get("name", "unknown")
        
        # check if already connected
        if server_name in _active_clients:
            return _active_clients[server_name]
        
        # stdio transport (local command)
        if "command" in server_config:
            command = server_config["command"]
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            
            logger.info(f"connecting to stdio mcp server: {server_name}")
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env if env else None
            )
            
            # create stdio client
            stdio_transport = await stdio_client(server_params)
            read, write = stdio_transport
            
            # create session
            session = ClientSession(read, write)
            await session.initialize()
            
            _active_clients[server_name] = session
            logger.info(f"connected to {server_name}")
            return session
        
        # http/sse transport (remote)
        elif "url" in server_config:
            from mcp.client.sse import sse_client
            
            url = server_config["url"]
            headers = server_config.get("headers", {})
            
            logger.info(f"connecting to http mcp server: {server_name}")
            
            # create sse client
            async with sse_client(url, headers=headers) as (read, write):
                session = ClientSession(read, write)
                await session.initialize()
                
                _active_clients[server_name] = session
                logger.info(f"connected to {server_name}")
                return session
        
        else:
            logger.error(f"no valid transport config for {server_name}")
            return None
    
    except ImportError as e:
        logger.warning(f"mcp sdk not available for {server_config.get('name')}: {e}")
        return None
    except Exception as e:
        logger.error(f"failed to connect to mcp server {server_config.get('name')}: {e}")
        return None


async def get_server_tools(server_config: Dict[str, Any]) -> List[Callable]:
    """
    get tools from an mcp server and wrap them as function_tool
    
    args:
        server_config: server configuration dict
    
    returns:
        list of wrapped tool functions
    """
    try:
        session = await connect_mcp_server(server_config)
        if not session:
            return []
        
        # list available tools from server
        tools_list = await session.list_tools()
        
        if not tools_list or not tools_list.tools:
            logger.info(f"no tools found on server {server_config['name']}")
            return []
        
        wrapped_tools = []
        
        # wrap each mcp tool as function_tool
        for tool in tools_list.tools:
            tool_name = tool.name
            tool_description = tool.description or f"mcp tool: {tool_name}"
            
            # create wrapper function that calls the mcp tool
            async def mcp_tool_wrapper(*args, server_session=session, tool_name=tool_name, **kwargs):
                """dynamically generated wrapper for mcp tool"""
                try:
                    # call the actual mcp tool
                    result = await server_session.call_tool(tool_name, arguments=kwargs)
                    
                    # format result for agent
                    if hasattr(result, 'content') and result.content:
                        return str(result.content[0].text if result.content else "no result")
                    return str(result)
                
                except Exception as e:
                    return f"error calling mcp tool {tool_name}: {str(e)}"
            
            # set function metadata
            mcp_tool_wrapper.__name__ = tool_name
            mcp_tool_wrapper.__doc__ = tool_description
            
            # wrap with function_tool decorator
            wrapped = function_tool(mcp_tool_wrapper)
            wrapped_tools.append(wrapped)
        
        logger.info(f"loaded {len(wrapped_tools)} tools from {server_config['name']}")
        return wrapped_tools
    
    except Exception as e:
        logger.error(f"error getting tools from {server_config.get('name')}: {e}")
        return []


def get_all_mcp_tools(config_path: Optional[Path] = None) -> List[Callable]:
    """
    load all enabled mcp servers and get their tools
    
    args:
        config_path: path to mcp_servers.json
    
    returns:
        list of all mcp tool functions
    """
    servers = load_mcp_servers(config_path)
    
    if not servers:
        return []
    
    all_tools = []
    
    # need to run async operations
    loop = asyncio.get_event_loop()
    
    for server_config in servers:
        try:
            tools = loop.run_until_complete(get_server_tools(server_config))
            all_tools.extend(tools)
        except Exception as e:
            logger.error(f"error loading tools from {server_config['name']}: {e}")
    
    logger.info(f"loaded {len(all_tools)} total mcp tools")
    return all_tools


async def cleanup_mcp_clients():
    """cleanup all active mcp client connections"""
    for name, client in _active_clients.items():
        try:
            if hasattr(client, 'close'):
                await client.close()
            logger.info(f"closed mcp client: {name}")
        except Exception as e:
            logger.error(f"error closing {name}: {e}")
    
    _active_clients.clear()

