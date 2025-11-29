
from livekit import agents
import inspect

try:
    session = agents.AgentSession()
    sig = inspect.signature(session.start)
    print(f"Signature: {sig}")
    for name, param in sig.parameters.items():
        print(f"Param: {name}, Kind: {param.kind}")
        
except Exception as e:
    print(f"\nError: {e}")
