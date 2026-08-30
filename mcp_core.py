from tools import TOOLS


class MCPServer:


    def __init__(self):

        self.tools = TOOLS



    def list_tools(self):

        """
        返回所有工具描述
        """

        result = []


        for tool in self.tools.values():

            result.append(
                tool.schema()
            )


        return result

    def call_tool(
        self,
        name,
        arguments
    ):

        if name not in self.tools:

            raise Exception(
                f"Tool不存在:{name}"
            )


        tool = self.tools[name]


        return tool.func(
            **arguments
        )