import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MOBIUS_MCP_URL", "http://localhost:9000/mcp")
MCP_TIMEOUT = float(os.getenv("MOBIUS_MCP_TIMEOUT", "10"))
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
LLM_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "30"))
TASK_MAX_STEPS = int(os.getenv("MOBIUS_TASK_MAX_STEPS", "20"))
TASK_TIMEOUT = float(os.getenv("MOBIUS_TASK_TIMEOUT", "600"))
TASK_LLM_RETRIES = int(os.getenv("MOBIUS_TASK_LLM_RETRIES", "1"))
TASK_TOOL_RETRIES = int(os.getenv("MOBIUS_TASK_TOOL_RETRIES", "1"))
TASK_MAX_TOOL_RESULT_CHARS = int(os.getenv("MOBIUS_TASK_MAX_TOOL_RESULT_CHARS", "8192"))
TASK_MAX_CONTEXT_CHARS = int(os.getenv("MOBIUS_TASK_MAX_CONTEXT_CHARS", "32768"))
