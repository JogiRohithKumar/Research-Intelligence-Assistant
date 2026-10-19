"""
Resilient execution utility for external and third-party API calls with safe fallback.
Protects the pipeline from unhandled crashes on provider timeouts, HTTP 429, or 500 errors.
"""

import logging
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger("research_assistant")


def safe_execute(*args, **kwargs) -> Any:
    """
    Executes a callable, catching exceptions and returning either:
      1. {"success": True/False, "result": ..., "error": ...} when called with (name: str, func: Callable, *func_args)
      2. result or default_return when called with (func: Callable, default_return=...)
    """
    if not args:
        return None

    first_arg = args[0]

    # Pattern 1: safe_execute(name: str, func: Callable, *func_args, **func_kwargs)
    if isinstance(first_arg, str):
        agent_name = first_arg
        func = args[1]
        func_args = args[2:]
        try:
            res = func(*func_args, **kwargs)
            return {"success": True, "result": res, "error": None}
        except Exception as e:
            logger.warning(f"[{agent_name}] execution failed with safe fallback: {e}")
            return {"success": False, "result": None, "error": str(e)}

    # Pattern 2: safe_execute(func: Callable, default_return: Any = None)
    elif callable(first_arg):
        func = first_arg
        default_return = kwargs.get("default_return", None)
        if len(args) > 1 and "default_return" not in kwargs:
            default_return = args[1]
        try:
            return func()
        except Exception as e:
            logger.warning(f"safe_execute caught exception: {e}")
            return default_return

    return None