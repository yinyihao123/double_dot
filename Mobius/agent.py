import json
import logging
import time
from llm import ask_llm_agent
import mcp_client
from tool_result import failure
logger = logging.getLogger(__name__)

def validate_action(action, tools):

    tool_name = action.get("action")

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

def _run_agent(question, llm=ask_llm_agent, client=mcp_client, max_steps=5,
              max_json_retries=2, trace_callback=None, max_context_chars=None,
              should_cancel=None):
    tools = client.list_tools()
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


    invalid_json_retries = 0
    for step in range(1, max_steps + 1):
        if should_cancel and should_cancel():
            return "失败：任务已取消。"

        llm_started = time.monotonic()
        try:
            response = llm(context)
        except Exception as exc:
            if trace_callback:
                trace_callback.on_error(step, "llm", str(exc), (time.monotonic() - llm_started) * 1000)
            raise
        if trace_callback:
            trace_callback.on_llm_call(step, len(context), response,
                                       (time.monotonic() - llm_started) * 1000)


        json_text = extract_json(response)

        if not json_text:
            invalid_json_retries += 1
            if invalid_json_retries > max_json_retries:
                return "失败：LLM 多次返回非法 JSON（无效 JSON）。"
            context += "\n请只返回有效 JSON。\n"
            continue
        try:
            action = json.loads(json_text)
        except json.JSONDecodeError:
            invalid_json_retries += 1
            if invalid_json_retries > max_json_retries:
                return "失败：LLM 多次返回非法 JSON。"
            context += "\n请修正为有效 JSON。\n"
            continue

        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            invalid_json_retries += 1
            if invalid_json_retries > max_json_retries:
                return "失败：LLM 返回了非法 action。"
            context += "\n请返回包含 action 字段的 JSON 对象。\n"
            continue

        if trace_callback:
            trace_callback.on_action(step, action)

        if action.get("action") == "final":
            if trace_callback:
                trace_callback.on_final(step, action.get("answer", ""))
            return action["answer"]

        if action.get("action") == "plan":
            plan = action.get("plan", action.get("args", {}).get("steps", []))
            if not plan:
                context += "\n计划不能为空，请继续执行或返回 final。\n"
                continue
            if trace_callback and hasattr(trace_callback, "on_plan"):
                trace_callback.on_plan(step, plan)
            context += f"\n当前计划：{plan}\n请执行计划中的下一步。\n"
            continue

        if should_cancel and should_cancel():
            return "失败：任务已取消。"


        valid, error = validate_action(
            action,
            tools
        )


        if not valid:

            context += f"""

        你的工具调用不合法：

        {error}

        请重新生成正确JSON。

        """

            continue



        tool_name = action["action"]

        args = action.get("args", {})


        logger.info("调用工具: %s 参数: %s", tool_name, args)


        try:
            tool_started = time.monotonic()
            if trace_callback:
                trace_callback.on_tool_call(step, tool_name, args)
            result = client.call_tool(
                tool_name,
                args
            )


        except Exception as e:

            result = failure(str(e))
            if trace_callback:
                trace_callback.on_error(step, "tool", str(e), (time.monotonic() - tool_started) * 1000)
                trace_callback.on_tool_result(step, tool_name, result,
                                               (time.monotonic() - tool_started) * 1000)
        else:
            if trace_callback:
                trace_callback.on_tool_result(step, tool_name, result,
                                               (time.monotonic() - tool_started) * 1000)
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
        if max_context_chars and len(context) > max_context_chars:
            keep_head = min(2000, max_context_chars // 3)
            context = context[:keep_head] + "\n...[context truncated]...\n" + context[-(max_context_chars - keep_head - 30):]


    return f"失败：Agent 达到最大步骤数（{max_steps}）。"


def run_agent(question, llm=ask_llm_agent, client=mcp_client, max_steps=5,
              max_json_retries=2, trace_callback=None, max_context_chars=None,
              should_cancel=None):
    """Backward-compatible entry point backed by AgentRuntime."""
    from runtime import AgentRuntime
    return AgentRuntime(llm=llm, client=client, max_steps=max_steps,
                        max_json_retries=max_json_retries).run(
                            question, trace_callback=trace_callback,
                            max_context_chars=max_context_chars,
                            should_cancel=should_cancel)
