"""
auto-loads all tools from this directory
just drop .py files here with @function_tool decorators and they load automatically
"""

import os
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# auto-discover and import all tool modules
_tools_dir = Path(__file__).parent
_all_tools = []

for file in _tools_dir.glob("*.py"):
    if file.name.startswith("_"):
        continue
    
    module_name = file.stem
    try:
        module = importlib.import_module(f".{module_name}", package="mcp_client.tools")
        
        # grab all function_tool decorated functions
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '__wrapped__'):
                    _all_tools.append(attr)
        
        logger.info(f"loaded tool module: {module_name}")
    except Exception as e:
        logger.warning(f"could not load {module_name}: {e}")

logger.info(f"total tools loaded: {len(_all_tools)}")


def get_all_tools():
    """returns list of all auto-discovered tools"""
    return _all_tools

