"""simple calculator tool"""

from agents import function_tool
import math


@function_tool
def calculate(expression: str) -> str:
    """
    calculate math expressions like "2+2" or "sqrt(16)"
    supports: +, -, *, /, sqrt, log, sin, cos, tan, pi, e
    """
    try:
        # make it safe and simple
        safe_dict = {
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "pi": math.pi, "e": math.e, "abs": abs, "round": round,
            "pow": pow, "exp": math.exp,
        }
        
        result = eval(expression.replace("^", "**"), {"__builtins__": {}}, safe_dict)
        
        # clean up output
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 10) if isinstance(result, float) else result)
    
    except Exception as e:
        return f"error: {str(e)}"

