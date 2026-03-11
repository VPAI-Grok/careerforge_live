"""
Dump the exact tool schemas that ADK generates for the live agent.
"""
import pathlib, sys, json
from dotenv import load_dotenv
load_dotenv('career_counselor_agent/.env')

from career_counselor_agent.agent import live_agent
from google.adk.agents import Agent

# Get the tools from the live agent
print("=== LIVE AGENT TOOLS ===")
for tool in live_agent.tools:
    func = getattr(tool, '__wrapped__', tool)
    name = getattr(func, '__name__', str(func))
    print(f"\nTool: {name}")
    
    # Try to get the function declaration
    import inspect
    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        annotation = param.annotation
        default = param.default
        print(f"  {param_name}: {annotation} = {default}")
