import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# How many times the agent is allowed to revise its decision after a
# validation failure before the run is escalated to a human.
MAX_AGENT_REVISIONS = int(os.getenv("MAX_AGENT_REVISIONS", "2"))

# How many tool-use turns the agent gets to investigate before it must submit.
MAX_TOOL_TURNS = int(os.getenv("MAX_TOOL_TURNS", "8"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
