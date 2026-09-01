"""Small runtime boundary around the existing Agent execution loop."""
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
import threading


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class AgentSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentContext:
    goal: str
    steps: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    plan: str | None = None
    phase: str = "planning"
    summary: str | None = None
    next_action: str | None = None

    def record_step(self, step, event_type, **data):
        self.steps.append({"step": step, "type": event_type, **data})

    def record_tool_result(self, step, name, result):
        self.tool_results.append({"step": step, "name": name, "result": result})

    def latest_result(self):
        return self.tool_results[-1] if self.tool_results else None

    def snapshot(self):
        return {"goal": self.goal, "phase": self.phase, "plan": self.plan,
                "next_action": self.next_action,
                "steps": list(self.steps), "tool_results": list(self.tool_results),
                "summary": self.summary}

    def compact(self, max_events):
        if not max_events or len(self.steps) <= max_events:
            return
        dropped = len(self.steps) - max_events
        self.steps = self.steps[-max_events:]
        previous = self.summary or ""
        self.summary = f"{previous}已压缩{dropped}个早期事件。"[-1000:]


@dataclass
class AgentState:
    status: TaskStatus = TaskStatus.PENDING
    step: int = 0
    error: str | None = None
    result: str | None = None
    cancel_requested: bool = False


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: str | None = None
    error: str | None = None
    steps: int = 0
    trace: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)


class TaskManager:
    """In-memory task registry for the first runtime iteration."""

    def __init__(self, runtime_factory, store=None):
        self.runtime_factory = runtime_factory
        self.store = store
        self.tasks = {}
        self._task_locks = {}
        if self.store and hasattr(self.store, "mark_interrupted"):
            self.store.mark_interrupted()

    def create(self, question, **kwargs):
        runtime = self.runtime_factory(**kwargs)
        runtime.context = AgentContext(goal=question)
        self.tasks[runtime.session.session_id] = runtime
        self._task_locks[runtime.session.session_id] = threading.Lock()
        if self.store:
            self.store.save(self.snapshot(runtime.session.session_id))
        return runtime.session.session_id

    def get(self, task_id):
        return self.tasks.get(task_id)

    def list_snapshots(self):
        snapshots = {task_id: self.snapshot(task_id) for task_id in self.tasks}
        if self.store:
            for saved in self.store.list():
                snapshots.setdefault(saved["task_id"], saved)
        return list(snapshots.values())

    def run(self, task_id, question, trace_callback=None):
        runtime = self.get(task_id)
        if runtime is None:
            raise KeyError(f"Task不存在:{task_id}")
        lock = self._task_locks.setdefault(task_id, threading.Lock())
        if not lock.acquire(blocking=False):
            return TaskResult(task_id, TaskStatus.FAILED,
                              error="任务正在运行，不能重复执行。")
        try:
            # Persist the transition before potentially long-running LLM/tool work.
            # This keeps polling clients truthful while the task is still executing.
            runtime.state.status = TaskStatus.RUNNING
            runtime.session.updated_at = time.time()
            if self.store:
                self.store.save(self.snapshot(task_id))
            if trace_callback is None:
                result = runtime.run_task(question)
            else:
                result = runtime.run_task(question, trace_callback=trace_callback)
        finally:
            lock.release()
        if self.store:
            self.store.save(self.snapshot(task_id))
        return result

    def cancel(self, task_id):
        runtime = self.get(task_id)
        if runtime is None:
            raise KeyError(f"Task不存在:{task_id}")
        runtime.cancel()
        if self.store:
            self.store.save(self.snapshot(task_id))
        return runtime.state.status

    def resume(self, task_id, trace_callback=None):
        """Resume a persisted failed/cancelled task using its original goal."""
        runtime = self.get(task_id)
        if runtime is None and self.store:
            saved = self.store.get(task_id)
            if saved is None:
                raise KeyError(f"Task不存在:{task_id}")
            if saved["status"] not in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
                raise ValueError("只有失败或取消的任务可以恢复。")
            runtime = self.runtime_factory()
            runtime.session.session_id = task_id
            runtime.context = AgentContext(goal=saved["goal"])
            runtime.context.phase = saved.get("phase") or "planning"
            runtime.context.plan = saved.get("plan")
            if saved.get("latest_tool"):
                runtime.context.record_tool_result(
                    saved.get("step", 0), saved["latest_tool"], "restored from persistence")
            runtime.state.status = TaskStatus(saved["status"])
            runtime.state.error = saved.get("error")
            self.tasks[task_id] = runtime
            self._task_locks[task_id] = threading.Lock()
        if runtime is None:
            raise KeyError(f"Task不存在:{task_id}")
        if runtime.state.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise ValueError("只有失败或取消的任务可以恢复。")
        runtime.state.cancel_requested = False
        goal = runtime.context.goal
        return self.run(task_id, goal, trace_callback=trace_callback)

    def snapshot(self, task_id):
        runtime = self.get(task_id)
        if runtime is None:
            if self.store:
                saved = self.store.get(task_id)
                if saved is not None:
                    return saved
            raise KeyError(f"Task不存在:{task_id}")

        return self._snapshot_runtime(runtime, task_id)

    def _snapshot_runtime(self, runtime, task_id):
        context = runtime.context
        latest = context.latest_result() if context else None
        snapshot = {
            "task_id": task_id,
            "status": runtime.state.status.value,
            "goal": runtime.context.goal if runtime.context else None,
            "step": runtime.state.step,
            "result": runtime.state.result,
            "error": runtime.state.error,
            "created_at": runtime.session.created_at,
            "updated_at": runtime.session.updated_at,
            "phase": context.phase if context else "planning",
            "plan": context.plan if context else None,
            "next_action": context.next_action if context else None,
            "latest_tool": latest["name"] if latest else None,
            "trace": list(getattr(runtime, "trace", [])),
            "trace_count": len(getattr(runtime, "trace", [])),
            "recent_trace": getattr(runtime, "trace", [])[-20:],
        }
        if self.store:
            self.store.save(snapshot)
        return snapshot


class _RuntimeObserver:
    def __init__(self, runtime, downstream=None):
        self.runtime = runtime
        self.downstream = downstream

    def _forward(self, method, *args):
        if self.downstream and hasattr(self.downstream, method):
            getattr(self.downstream, method)(*args)

    def on_llm_call(self, step, context_length, response, duration_ms):
        self.runtime.trace.append({"step": step, "type": "llm_call", "context_length": context_length, "response": response, "duration_ms": duration_ms})
        self.runtime.state.status = TaskStatus.RUNNING
        self.runtime.context.phase = "planning"
        self.runtime.state.step = max(self.runtime.state.step, step)
        self.runtime.context.record_step(step, "llm_call", context_length=context_length)
        self.runtime.context.compact(self.runtime.max_context_events)
        self._forward("on_llm_call", step, context_length, response, duration_ms)

    def on_action(self, step, action):
        self.runtime.trace.append({"step": step, "type": "action", "action": action})
        self.runtime.state.step = max(self.runtime.state.step, step)
        if isinstance(action, dict) and action.get("action") == "plan":
            self.runtime.context.plan = action.get("plan", action.get("args", {}).get("steps"))
        self.runtime.context.record_step(step, "action", action=action)
        self.runtime.context.compact(self.runtime.max_context_events)
        self._forward("on_action", step, action)

    def on_plan(self, step, plan):
        self.runtime.trace.append({"step": step, "type": "plan", "plan": plan})
        self.runtime.context.plan = plan
        self.runtime.context.next_action = "execute"
        self.runtime.context.phase = "planning"
        self.runtime.context.record_step(step, "plan", plan=plan)
        self._forward("on_plan", step, plan)

    def on_tool_call(self, step, name, arguments):
        self.runtime.trace.append({"step": step, "type": "tool_call", "name": name, "arguments": arguments})
        self.runtime.context.next_action = "observe"
        self.runtime.state.status = TaskStatus.WAITING
        self.runtime.context.phase = "executing"
        self.runtime.context.record_step(step, "tool_call", name=name, arguments=arguments)
        self.runtime.context.compact(self.runtime.max_context_events)
        self._forward("on_tool_call", step, name, arguments)

    def on_tool_result(self, step, name, result, duration_ms):
        stored = result
        truncated = False
        limit = self.runtime.max_tool_result_chars
        if limit and isinstance(result, str) and len(result) > limit:
            stored, truncated = result[:limit], True
        self.runtime.trace.append({"step": step, "type": "tool_result", "name": name,
                                   "result": stored, "truncated": truncated, "duration_ms": duration_ms})
        self.runtime.state.status = TaskStatus.RUNNING
        self.runtime.context.phase = "observing"
        self.runtime.context.record_tool_result(step, name, stored)
        self.runtime.context.next_action = "replan"
        self.runtime.context.compact(self.runtime.max_context_events)
        self._forward("on_tool_result", step, name, result, duration_ms)

    def on_final(self, step, answer):
        self.runtime.trace.append({"step": step, "type": "final", "answer": answer})
        self.runtime.state.status = TaskStatus.COMPLETED
        self.runtime.context.phase = "finalizing"
        self.runtime.context.next_action = None
        self._forward("on_final", step, answer)

    def on_error(self, step, layer, error, duration_ms=0.0):
        self.runtime.trace.append({"step": step, "type": "error", "layer": layer, "error": error, "duration_ms": duration_ms})
        self.runtime.state.error = error
        self._forward("on_error", step, layer, error, duration_ms)


class _RetryClient:
    def __init__(self, client, retries):
        self.client, self.retries = client, retries

    def list_tools(self):
        return self.client.list_tools()

    def call_tool(self, name, arguments):
        last_error = None
        for _ in range(self.retries + 1):
            try:
                return self.client.call_tool(name, arguments)
            except Exception as exc:
                last_error = exc
        raise last_error

class AgentRuntime:
    """Runtime facade; the existing loop remains the execution implementation."""

    def __init__(self, llm, client, max_steps=5, max_json_retries=2,
                 max_context_chars=None, llm_retries=0, tool_retries=0,
                 timeout_seconds=None, max_context_events=None,
                 max_tool_result_chars=8192):
        self.llm = llm
        self.client = client
        self.max_steps = max_steps
        self.max_json_retries = max_json_retries
        self.max_context_chars = max_context_chars
        self.llm_retries = max(0, llm_retries)
        self.tool_retries = max(0, tool_retries)
        self.timeout_seconds = timeout_seconds
        self.max_context_events = max_context_events
        self.max_tool_result_chars = max(0, int(max_tool_result_chars or 0))
        self._deadline = None
        self._timed_out = False
        self.session = AgentSession()
        self.state = AgentState()
        self.context = None
        self.trace = []

    def cancel(self):
        if self.state.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING):
            self.state.cancel_requested = True
            self.state.status = TaskStatus.CANCELLED
            if self.context is not None:
                self.context.phase = "cancelled"

    def run(self, question, trace_callback=None, max_context_chars=None, should_cancel=None):
        task = self.run_task(question, trace_callback=trace_callback,
                             max_context_chars=max_context_chars,
                             should_cancel=should_cancel)
        if task.result is not None:
            return task.result
        if task.status == TaskStatus.CANCELLED:
            return "失败：任务已取消。"
        return "失败：" + (task.error or "任务执行失败。")

    def run_task(self, question, trace_callback=None, max_context_chars=None, should_cancel=None):
        if self.state.cancel_requested:
            return TaskResult(self.session.session_id, TaskStatus.CANCELLED)
        self.state.status = TaskStatus.RUNNING
        self.context = AgentContext(goal=question)
        self.trace = []
        self.session.updated_at = time.time()
        self._deadline = (time.monotonic() + self.timeout_seconds
                          if self.timeout_seconds is not None else None)
        self._timed_out = False
        observer = _RuntimeObserver(self, trace_callback)
        try:
            from agent import _run_agent
            client = (_RetryClient(self.client, self.tool_retries)
                      if self.tool_retries else self.client)
            answer = _run_agent(question, llm=self._call_llm, client=client,
                                max_steps=self.max_steps,
                                max_json_retries=self.max_json_retries,
                                trace_callback=observer,
                                max_context_chars=(max_context_chars if max_context_chars is not None else self.max_context_chars),
                                should_cancel=(should_cancel or self._should_stop))
            self.state.result = answer
            failed = isinstance(answer, str) and answer.startswith("失败：")
            self.state.status = TaskStatus.FAILED if failed else TaskStatus.COMPLETED
            if failed:
                self.state.error = answer
                self.context.phase = "error"
                if self.state.cancel_requested and not self._timed_out:
                    self.state.status = TaskStatus.CANCELLED
                    self.context.phase = "cancelled"
            self.session.updated_at = time.time()
            return TaskResult(self.session.session_id, self.state.status,
                              result=answer, error=answer if failed else None,
                              steps=self.state.step, trace=list(self.trace),
                              context=self.context.snapshot())
        except Exception as exc:
            self.state.error = str(exc)
            self.state.status = TaskStatus.FAILED
            if self.context is not None:
                self.context.phase = "error"
            self.session.updated_at = time.time()
            return TaskResult(self.session.session_id, TaskStatus.FAILED,
                              error=str(exc), steps=self.state.step, trace=list(self.trace),
                              context=self.context.snapshot() if self.context else {})

    def _call_llm(self, context):
        if self.context and self.context.summary:
            context = ("[Runtime context summary]\n"
                       f"goal: {self.context.goal}\n"
                       f"phase: {self.context.phase}\n"
                       f"summary: {self.context.summary}\n\n" + context)
        last_error = None
        for _ in range(self.llm_retries + 1):
            try:
                return self.llm(context)
            except Exception as exc:
                last_error = exc
        raise last_error

    def _should_stop(self):
        if self.state.cancel_requested:
            return True
        if self._deadline is not None and time.monotonic() >= self._deadline:
            self.state.error = "失败：任务超时。"
            self._timed_out = True
            self.state.cancel_requested = True
            return True
        return False
