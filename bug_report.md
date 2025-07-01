# Bug Report: 3 Bugs Found in AgentOps Codebase

## Bug 1: Security Vulnerability - Unsafe eval() in LangGraph Example

### Location
File: `examples/langgraph/langgraph_example.py`, line 32

### Description
The `calculate` tool function uses Python's `eval()` function to evaluate mathematical expressions from user input without any sanitization. This is a critical security vulnerability that allows arbitrary code execution.

```python
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)  # UNSAFE!
        return f"The result is: {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"
```

### Impact
An attacker could execute arbitrary Python code by passing malicious expressions like:
- `__import__('os').system('rm -rf /')`
- `__import__('subprocess').run(['cat', '/etc/passwd'])`
- Access to internal variables and functions

### Fix
Replace `eval()` with a safe mathematical expression parser:

```python
import ast
import operator

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    # Define allowed operators
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    def evaluate_node(node):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp):
            left = evaluate_node(node.left)
            right = evaluate_node(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = evaluate_node(node.operand)
            return allowed_operators[type(node.op)](operand)
        else:
            raise ValueError(f"Unsupported operation: {type(node).__name__}")
    
    try:
        # Parse the expression into an AST
        tree = ast.parse(expression, mode='eval')
        # Evaluate the AST safely
        result = evaluate_node(tree.body)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"
```

---

## Bug 2: Thread Safety Issue - Race Condition in Client Singleton

### Location
File: `agentops/client/client.py`, lines 50-56

### Description
The Client singleton implementation has a race condition in the `__new__` method. Multiple threads could simultaneously check `cls.__instance is None` and create multiple instances before the assignment completes.

```python
def __new__(cls, *args: Any, **kwargs: Any) -> "Client":
    if cls.__instance is None:  # Thread 1 and 2 both see None
        cls.__instance = super(Client, cls).__new__(cls)  # Both create instances
        # Initialize instance variables...
        cls.__instance._init_trace_context = None
        cls.__instance._legacy_session_for_init_trace = None
    return cls.__instance
```

### Impact
- Multiple Client instances could be created in multi-threaded applications
- Inconsistent state between threads
- Potential data corruption or lost traces

### Fix
The `agentops/__init__.py` file already implements proper thread-safe singleton access using a lock. The Client class should either:
1. Use the same pattern internally, or
2. Be accessed only through the thread-safe `get_client()` function

Fixed implementation for Client.__new__:

```python
_instance_lock = threading.Lock()

def __new__(cls, *args: Any, **kwargs: Any) -> "Client":
    if cls.__instance is None:
        with cls._instance_lock:
            # Double-check locking pattern
            if cls.__instance is None:
                cls.__instance = super(Client, cls).__new__(cls)
                # Initialize instance variables...
                cls.__instance._init_trace_context = None
                cls.__instance._legacy_session_for_init_trace = None
    return cls.__instance
```

---

## Bug 3: Resource Management - Bare except Clauses Hide Errors

### Location
Multiple files, particularly:
- `agentops/helpers/system.py` (lines 59, 84, 91, 98, 110, 122, 135)
- `agentops/helpers/serialization.py` (line 104)
- `tests/integration/test_session_concurrency.py` (lines 51-52)

### Description
The codebase uses bare `except:` clauses in many places, which catch all exceptions including `SystemExit`, `KeyboardInterrupt`, and other critical exceptions. This can:
1. Hide programming errors
2. Prevent proper cleanup on shutdown
3. Make debugging difficult
4. Catch exceptions that should propagate (like `KeyboardInterrupt`)

Example from `agentops/helpers/system.py`:
```python
def get_sdk_details():
    try:
        return {
            "AgentOps SDK Version": get_agentops_version(),
            "Python Version": platform.python_version(),
            "System Packages": get_sys_packages(),
        }
    except:  # BAD: Catches everything including KeyboardInterrupt
        return {}
```

### Impact
- Silent failures that make debugging difficult
- Inability to properly interrupt the program with Ctrl+C
- Hidden errors that could indicate serious problems
- Resource leaks when cleanup code is skipped

### Fix
Replace bare `except:` with specific exception handling:

```python
def get_sdk_details():
    try:
        return {
            "AgentOps SDK Version": get_agentops_version(),
            "Python Version": platform.python_version(),
            "System Packages": get_sys_packages(),
        }
    except Exception as e:  # Catch only Exception and subclasses
        logger.debug(f"Error getting SDK details: {e}")
        return {}
```

For the test file `test_session_concurrency.py`:
```python
try:
    agentops.end_all_sessions()
except Exception as e:  # Don't catch KeyboardInterrupt/SystemExit
    logger.debug(f"Error ending sessions: {e}")
    pass  # Still ignore the error, but log it
```

### Additional Recommendations
1. Use `except Exception:` instead of bare `except:`
2. Log the exceptions for debugging
3. Consider if the exception should be re-raised after logging
4. For specific expected exceptions, catch them explicitly (e.g., `except (ValueError, TypeError):`)

---

## Summary

These three bugs represent common but serious issues in Python applications:

1. **Security vulnerability** through unsafe code execution
2. **Concurrency bug** that could cause race conditions in multi-threaded environments  
3. **Error handling anti-pattern** that hides problems and makes debugging difficult

All three bugs have been identified with specific locations and provided with detailed fixes that maintain the intended functionality while addressing the underlying issues.