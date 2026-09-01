from tool_core import Tool


class ToolRegistry:

    def __init__(self):
        self.tools = {}


    def register(self, tool: Tool):

        self.tools[tool.name] = tool


    def get(self, name):

        return self.tools.get(name)


    def has_tool(self, name):

        return name in self.tools


    def list_tools(self):

        return [
            tool.schema()
            for tool in self.tools.values()
        ]


    def call(self, name, args):

        if name not in self.tools:
            raise Exception(
                f"Tool不存在:{name}"
            )

        tool = self.tools[name]

        return tool.func(**args)