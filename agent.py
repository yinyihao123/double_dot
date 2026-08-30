import json
import re
from llm import ask_llm_agent
import mcp_client
from tool_result import failure

def validate_action(action, tools):

    tool_name = action.get("action")

    tools = mcp_client.list_tools()


    target_tool = None


    for tool in tools:

        if tool["name"] == tool_name:
            target_tool = tool
            break


    if target_tool is None:

        return False,f"不存在工具:{tool_name}"


    args = action.get("args", {})


    required_params = target_tool.get(
        "required",
        []
    )


    for param in required_params:

        if param not in args:

            return False,f"缺少参数:{param}"


    return True,None

def extract_json(text):

    start = text.find("{")

    end = text.rfind("}")

    if start != -1 and end != -1:

        return text[start:end+1]

    return None

def run_agent(question):
    tools = mcp_client.list_tools()
    context = f"""
你是一个Agent。

你有以下工具：

{json.dumps(
    tools,
    ensure_ascii=False,
    indent=2
)}


用户问题：

{question}


如果需要调用工具：

你必须只输出JSON。

禁止输出任何解释。
禁止输出Markdown。
禁止输出代码块。

正确格式：

{{
 "action":"工具名称",
 "args":{{
    "参数名":"参数值"
 }}
}}


例如：

{{
 "action":"search_file",
 "args":{{
    "keyword":"error"
 }}
}}


如果工具不需要参数：

args返回空对象：

{{
 "action":"get_time",
 "args":{{}}
}}


如果任务完成：

返回:

{{
 "action":"final",
 "answer":"最终回答"
}}

"""


    while True:

        response = ask_llm_agent(context)


        print("LLM:", response)

        print("原始LLM返回:", repr(response))
        json_text = extract_json(response)

        if not json_text:
            raise Exception("LLM没有返回JSON")
        
        print("准备解析JSON:", repr(json_text))
        
        action = json.loads(json_text)

        if action["action"] == "final":

            return action["answer"]


        valid, error = validate_action(
            action,
            tools
        )


        if not valid:

            print("Action非法:", error)


            context += f"""

        你的工具调用不合法：

        {error}

        请重新生成正确JSON。

        """

            continue



        tool_name = action["action"]

        args = action.get("args", {})


        print("调用工具:", tool_name)
        print("参数:", args)


        try:

            result = mcp_client.call_tool(
                tool_name,
                args
            )


        except Exception as e:

            result = failure(str(e))
        print("工具返回:", result)


        context += f"""

工具:
{tool_name}

结果:
{json.dumps(
    result,
    ensure_ascii=False,
    indent=2
)}

请继续判断下一步。

"""