from fastapi import BackgroundTasks, FastAPI, HTTPException
from agent import run_agent
import mcp_client
from llm import ask_llm_agent
from runtime import AgentRuntime, TaskManager, TaskStatus
from task_store import SQLiteTaskStore
from config import (TASK_LLM_RETRIES, TASK_MAX_STEPS, TASK_TIMEOUT,
                    TASK_TOOL_RETRIES, TASK_MAX_TOOL_RESULT_CHARS)
from config import TASK_MAX_CONTEXT_CHARS


app = FastAPI()


task_manager = TaskManager(
    lambda **_: AgentRuntime(ask_llm_agent, mcp_client,
                             max_steps=TASK_MAX_STEPS,
                             timeout_seconds=TASK_TIMEOUT,
                             llm_retries=TASK_LLM_RETRIES,
                             tool_retries=TASK_TOOL_RETRIES,
                             max_tool_result_chars=TASK_MAX_TOOL_RESULT_CHARS,
                             max_context_chars=TASK_MAX_CONTEXT_CHARS),
    store=SQLiteTaskStore()
)


def _run_task(task_id, question):
    task_manager.run(task_id, question)


@app.get("/")
def home():
    return {
        "message": "My Agent is running"
    }


@app.get("/chat")
def chat(question: str):

    answer = run_agent(question)

    return {
        "question": question,
        "answer": answer
    }


@app.post("/tasks", status_code=202)
def create_task(payload: dict, background_tasks: BackgroundTasks):
    question = payload.get("question") or payload.get("goal")
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    task_id = task_manager.create(question)
    background_tasks.add_task(_run_task, task_id, question)
    return {"task_id": task_id, "status": "PENDING", "goal": question}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    try:
        return task_manager.snapshot(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks")
def list_tasks():
    return {"tasks": task_manager.list_snapshots()}


@app.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    try:
        status = task_manager.cancel(task_id)
        return {"task_id": task_id, "status": status.value}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tasks/{task_id}/resume")
def resume_task(task_id: str, background_tasks: BackgroundTasks):
    try:
        snapshot = task_manager.snapshot(task_id)
        if snapshot["status"] not in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            raise ValueError("只有失败或取消的任务可以恢复。")
        background_tasks.add_task(task_manager.resume, task_id)
        return {"task_id": task_id, "status": "PENDING"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
