import json
import inspect
from typing import Any, Callable, Dict, List, Optional
from mcp import Tool as MCPTool
from agents import function_tool

def convert_mcp_tool_to_python_callable(tool: MCPTool, execute_fn: Callable) -> Callable:
    """
    Converts an MCP Tool definition into a Python callable that can be used by the Agent.
    
    Uses the @function_tool decorator from the agents library to ensure proper compatibility.
    
    Args:
        tool: The MCP Tool object containing name, description, and input_schema.
        execute_fn: A function that takes (tool_name, arguments) and executes the tool.
        
    Returns:
        A callable function that wraps the MCP tool execution.
    """
    
    tool_name = tool.name
    description = tool.description or ""
    input_schema = tool.inputSchema or {}
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    docstring = f"{description}\n\nArgs:\n"
    for prop_name, prop_schema in properties.items():
        prop_desc = prop_schema.get("description", "")
        prop_type = prop_schema.get("type", "any")
        is_required = " (required)" if prop_name in required else " (optional)"
        docstring += f"    {prop_name} ({prop_type}): {prop_desc}{is_required}\n"
    
    type_str_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "object": "str", 
        "array": "str" 
    }
    
    param_type_strs = {}
    for prop_name, prop_schema in properties.items():
        json_type = prop_schema.get("type", "string")
        
        
        if json_type == "array":
            items_schema = prop_schema.get("items", {})
            item_type = items_schema.get("type", "string")
            if item_type in ["string", "integer", "number", "boolean"]:
                mapped_item_type = type_str_mapping.get(item_type, "str")
                param_type_strs[prop_name] = f"List[{mapped_item_type}]"
            else:
                param_type_strs[prop_name] = "str"
        else:
            param_type_strs[prop_name] = type_str_mapping.get(json_type, "str")
            
    
    param_names = list(properties.keys())
    param_str = ", ".join(f"{name}: {param_type_strs[name]}" for name in param_names)
    
    func_code = f"""
async def {tool_name}({param_str}) -> str:
    '''Dynamic wrapper for MCP tool.'''
    kwargs = {{}}
    import json
    
    def parse_if_needed(val, expected_type):
        if expected_type == 'object' or expected_type == 'array':
            if isinstance(val, str):
                try:
                    if val.strip().startswith(('{{', '[')):
                        return json.loads(val)
                except:
                    pass
        return val

"""
    
    for name in param_names:
        prop_schema = properties.get(name, {})
        json_type = prop_schema.get("type", "string")
        is_forced_string = False
        if json_type == "object":
            is_forced_string = True
        elif json_type == "array":
             items_schema = prop_schema.get("items", {})
             item_type = items_schema.get("type", "string")
             if item_type not in ["string", "integer", "number", "boolean"]:
                 is_forced_string = True
        
        if is_forced_string:
             func_code += f"    kwargs['{name}'] = parse_if_needed({name}, '{json_type}')\n"
        else:
             func_code += f"    kwargs['{name}'] = {name}\n"

    func_code += f"""
    try:
        result = await execute_fn(tool_name_var, kwargs)
        
        if hasattr(result, 'content') and isinstance(result.content, list):
            text_output = []
            for item in result.content:
                if item.type == 'text':
                    text_output.append(item.text)
                elif item.type == 'image':
                    text_output.append(f"[Image: {{item.mimeType}}]")
                elif item.type == 'resource':
                    text_output.append(f"[Resource: {{item.uri}}]")
            return "\\n".join(text_output)
        
        return str(result)
    except Exception as e:
        return f"Error executing tool {{tool_name_var}}: {{str(e)}}"
"""
    
    local_vars = {
        "execute_fn": execute_fn,
        "tool_name_var": tool_name,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "dict": dict,
        "list": list,
        "List": List,
        "hasattr": hasattr,
        "isinstance": isinstance
    }
    exec(func_code, local_vars)
    
    dynamic_func = local_vars[tool_name]
    
    dynamic_func.__doc__ = docstring
    
    wrapped_func = function_tool(dynamic_func)
    
    return wrapped_func
