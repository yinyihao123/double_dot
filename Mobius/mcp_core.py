from tool_registry import ToolRegistry


class MCPServer:


    def __init__(self, registry: ToolRegistry):
        self.registry = registry



    def list_tools(self):

        """
        返回所有工具描述
        """

        return self.registry.list_tools()

    def call_tool(
        self,
        name,
        arguments
    ):

        return self.registry.call(name, arguments)
