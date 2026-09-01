from tool_registry import ToolRegistry

from tools.system import tools as system_tools
from tools.workspace import tools as workspace_tools



registry = ToolRegistry()


for tool in system_tools + workspace_tools:

    registry.register(tool)
