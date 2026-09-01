from runtime import AgentRuntime, TaskManager, TaskStatus


class FakeClient:
    def list_tools(self):
        return [{"name": "get_time", "description": "time", "parameters": {}, "required": []}]

    def call_tool(self, name, args):
        return "12:00"


def test_runtime_wraps_legacy_loop():
    responses = iter([
        '{"action":"get_time","args":{}}',
        '{"action":"final","answer":"12:00"}',
    ])
    runtime = AgentRuntime(lambda _: next(responses), FakeClient(), max_steps=3)
    assert runtime.run("time") == "12:00"
    assert runtime.state.status == TaskStatus.COMPLETED
    assert runtime.session.session_id
    assert runtime.state.step == 2
    assert runtime.context.tool_results[0]["name"] == "get_time"
    assert runtime.context.latest_result()["result"] == "12:00"
    assert runtime.context.phase == "finalizing"


def test_runtime_supports_optional_plan_action():
    responses = iter([
        '{"action":"plan","plan":["get time"]}',
        '{"action":"get_time","args":{}}',
        '{"action":"final","answer":"12:00"}',
    ])
    runtime = AgentRuntime(lambda _: next(responses), FakeClient(), max_steps=4)
    assert runtime.run("time") == "12:00"
    assert runtime.context.plan == ["get time"]
    assert runtime.trace[-1]["type"] == "final"
    assert any(event["type"] == "tool_result" for event in runtime.trace)


def test_runtime_cancel_before_run():
    runtime = AgentRuntime(lambda _: "never", FakeClient())
    runtime.cancel()
    result = runtime.run_task("cancel")
    assert result.status == TaskStatus.CANCELLED


def test_runtime_marks_max_steps_failed():
    runtime = AgentRuntime(lambda _: '{"action":"get_time","args":{}}', FakeClient(), max_steps=1)
    result = runtime.run_task("time")
    assert result.status == TaskStatus.FAILED
    assert runtime.state.error.startswith("失败：")
    assert runtime.context.phase == "error"


def test_task_manager_create_run_cancel():
    manager = TaskManager(lambda **_: AgentRuntime(lambda _: '{"action":"final","answer":"ok"}', FakeClient()))
    task_id = manager.create("task")
    assert manager.get(task_id) is not None
    assert manager.run(task_id, "task").status == TaskStatus.COMPLETED
    snapshot = manager.snapshot(task_id)
    assert snapshot["status"] == "COMPLETED" and snapshot["goal"] == "task"
    assert snapshot["phase"] == "finalizing"
    assert snapshot["trace_count"] >= 3
    assert snapshot["recent_trace"][-1]["type"] == "final"
    assert any(item["task_id"] == task_id for item in manager.list_snapshots())
    other = manager.create("cancel")
    assert manager.cancel(other) == TaskStatus.CANCELLED


def test_task_manager_rejects_concurrent_run():
    import threading
    started = threading.Event()
    release = threading.Event()

    def llm(_):
        started.set()
        release.wait(1)
        return '{"action":"final","answer":"ok"}'

    manager = TaskManager(lambda **_: AgentRuntime(llm, FakeClient()))
    task_id = manager.create("concurrent")
    first = []
    worker = threading.Thread(target=lambda: first.append(manager.run(task_id, "concurrent")))
    worker.start()
    assert started.wait(1)
    second = manager.run(task_id, "concurrent")
    assert second.status == TaskStatus.FAILED
    assert "正在运行" in (second.error or "")
    release.set()
    worker.join(1)
    assert first and first[0].status == TaskStatus.COMPLETED


def test_task_manager_persists_running_before_work(tmp_path):
    from task_store import SQLiteTaskStore
    import threading
    started = threading.Event()
    release = threading.Event()

    def llm(_):
        started.set()
        release.wait(1)
        return '{"action":"final","answer":"ok"}'

    store = SQLiteTaskStore(str(tmp_path / "tasks.db"))
    manager = TaskManager(lambda **_: AgentRuntime(llm, FakeClient()), store=store)
    task_id = manager.create("persist running")
    worker = threading.Thread(target=lambda: manager.run(task_id, "persist running"))
    worker.start()
    assert started.wait(1)
    assert store.get(task_id)["status"] == "RUNNING"
    release.set()
    worker.join(1)


def test_runtime_context_limit_is_accepted():
    responses = iter(['{"action":"final","answer":"ok"}'])
    runtime = AgentRuntime(lambda context: next(responses), FakeClient(), max_context_chars=100)
    assert runtime.run("x") == "ok"


def test_context_event_compaction():
    from runtime import AgentContext
    context = AgentContext("goal")
    for i in range(5):
        context.record_step(i, "action")
    context.compact(2)
    assert len(context.steps) == 2 and context.summary


def test_runtime_injects_context_summary_after_compaction():
    from runtime import AgentContext
    seen = []
    runtime = AgentRuntime(lambda context: (seen.append(context) or '{"action":"final","answer":"ok"}'),
                           FakeClient(), max_context_events=1)
    runtime.context = AgentContext("goal")
    runtime.context.summary = "earlier tool result"
    runtime._call_llm("current context")
    assert "Runtime context summary" in seen[0]
    assert "earlier tool result" in seen[0]


def test_runtime_code_agent_workflow_offline():
    responses = iter([
        '{"action":"plan","plan":["inspect","write","test"]}',
        '{"action":"list_files","args":{"path":"."}}',
        '{"action":"write_file","args":{"path":"app.py","content":"print(1)"}}',
        '{"action":"run_shell","args":{"command":["python","-m","pytest"]}}',
        '{"action":"final","answer":"项目已创建并验证通过"}',
    ])
    class WorkflowClient:
        def __init__(self): self.calls = []
        def list_tools(self):
            return [
                {"name": "list_files", "description": "list", "parameters": {"path": {"type": "string"}}, "required": []},
                {"name": "write_file", "description": "write", "parameters": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
                {"name": "run_shell", "description": "test", "parameters": {"command": {"type": "array"}}, "required": ["command"]},
            ]
        def call_tool(self, name, args):
            self.calls.append((name, args))
            return {"success": True, "data": "ok", "error": None}
    client = WorkflowClient()
    runtime = AgentRuntime(lambda _: next(responses), client, max_steps=6)
    assert runtime.run("create and test project") == "项目已创建并验证通过"
    assert [name for name, _ in client.calls] == ["list_files", "write_file", "run_shell"]
    assert runtime.context.plan == ["inspect", "write", "test"]


def test_runtime_truncates_stored_tool_result():
    class LongClient(FakeClient):
        def call_tool(self, name, args):
            return "abcdefghij"
    responses = iter(['{"action":"get_time","args":{}}', '{"action":"final","answer":"ok"}'])
    runtime = AgentRuntime(lambda _: next(responses), LongClient(), max_tool_result_chars=4)
    assert runtime.run("time") == "ok"
    event = next(e for e in runtime.trace if e["type"] == "tool_result")
    assert event["result"] == "abcd" and event["truncated"] is True
    assert runtime.context.latest_result()["result"] == "abcd"


def test_runtime_trace_contains_failed_tool_result():
    class FailingClient(FakeClient):
        def call_tool(self, name, args):
            raise RuntimeError("boom")
    responses = iter(['{"action":"get_time","args":{}}', '{"action":"final","answer":"recovered"}'])
    runtime = AgentRuntime(lambda _: next(responses), FailingClient(), max_steps=3)
    assert runtime.run("time") == "recovered"
    types = [event["type"] for event in runtime.trace]
    assert "error" in types and "tool_result" in types
    failed = next(event for event in runtime.trace if event["type"] == "tool_result")
    assert failed["result"]["success"] is False


def test_runtime_replans_after_tool_failure():
    class RecoveringClient(FakeClient):
        def __init__(self): self.calls = 0
        def call_tool(self, name, args):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary failure")
            return "12:00"
    responses = iter([
        '{"action":"get_time","args":{}}',
        '{"action":"get_time","args":{}}',
        '{"action":"final","answer":"12:00"}',
    ])
    client = RecoveringClient()
    runtime = AgentRuntime(lambda _: next(responses), client, max_steps=4)
    assert runtime.run("time") == "12:00"
    assert client.calls == 2
    assert sum(e["type"] == "tool_call" for e in runtime.trace) == 2


def test_runtime_llm_retry():
    calls = [0]
    def flaky(_):
        calls[0] += 1
        if calls[0] == 1:
            raise RuntimeError("temporary")
        return '{"action":"final","answer":"ok"}'
    runtime = AgentRuntime(flaky, FakeClient(), llm_retries=1)
    assert runtime.run("retry") == "ok"
    assert calls[0] == 2


def test_runtime_tool_retry():
    calls = [0]
    class FlakyClient(FakeClient):
        def call_tool(self, name, args):
            calls[0] += 1
            if calls[0] == 1:
                raise RuntimeError("temporary tool failure")
            return "12:00"
    responses = iter([
        '{"action":"get_time","args":{}}',
        '{"action":"final","answer":"12:00"}',
    ])
    runtime = AgentRuntime(lambda _: next(responses), FlakyClient(), tool_retries=1)
    assert runtime.run("retry tool") == "12:00"
    assert calls[0] == 2


def test_runtime_cancellation_checked_during_loop():
    runtime = AgentRuntime(lambda _: '{"action":"get_time","args":{}}', FakeClient(), max_steps=3)
    runtime.state.cancel_requested = True
    result = runtime.run_task("cancel")
    assert result.status == TaskStatus.CANCELLED


def test_runtime_cancellation_between_steps():
    runtime = None
    def llm(_):
        runtime.state.cancel_requested = True
        return '{"action":"get_time","args":{}}'
    runtime = AgentRuntime(llm, FakeClient(), max_steps=3)
    result = runtime.run_task("cancel")
    assert result.status == TaskStatus.CANCELLED


def test_runtime_cancellation_before_tool_execution():
    runtime = None
    class TrackingClient(FakeClient):
        def call_tool(self, name, args):
            raise AssertionError("tool should not execute after cancellation")
    def llm(_):
        runtime.state.cancel_requested = True
        return '{"action":"get_time","args":{}}'
    runtime = AgentRuntime(llm, TrackingClient(), max_steps=3)
    result = runtime.run_task("cancel")
    assert result.status == TaskStatus.CANCELLED


def test_runtime_timeout_at_step_boundary():
    runtime = AgentRuntime(lambda _: '{"action":"final","answer":"ok"}', FakeClient(), timeout_seconds=0)
    result = runtime.run_task("timeout")
    assert result.status == TaskStatus.FAILED


def test_runtime_compatibility_returns_failure_text():
    runtime = AgentRuntime(lambda _: (_ for _ in ()).throw(RuntimeError("llm down")), FakeClient())
    assert runtime.run("failure").startswith("失败：llm down")


def test_sqlite_task_store(tmp_path):
    from task_store import SQLiteTaskStore
    from runtime import TaskManager
    store = SQLiteTaskStore(str(tmp_path / "tasks.db"))
    manager = TaskManager(lambda **_: AgentRuntime(lambda _: '{"action":"final","answer":"ok"}', FakeClient()), store=store)
    task_id = manager.create("persist")
    manager.run(task_id, "persist")
    saved = store.get(task_id)
    assert saved["status"] == "COMPLETED" and saved["goal"] == "persist"
    assert saved["phase"] == "finalizing"
    assert saved["trace"] and saved["trace"][-1]["type"] == "final"
    manager2 = TaskManager(lambda **_: AgentRuntime(lambda _: "never", FakeClient()), store=store)
    assert manager2.snapshot(task_id)["status"] == "COMPLETED"


def test_sqlite_marks_interrupted_tasks_failed(tmp_path):
    from task_store import SQLiteTaskStore
    store = SQLiteTaskStore(str(tmp_path / "tasks.db"))
    snapshot = {"task_id": "old", "status": "RUNNING", "goal": "old task", "result": None, "error": None, "step": 1, "created_at": 1.0, "updated_at": 1.0}
    store.save(snapshot)
    TaskManager(lambda **_: AgentRuntime(lambda _: "never", FakeClient()), store=store)
    saved = store.get("old")
    assert saved["status"] == "FAILED"
    assert saved["error"] == "任务因进程重启而中断。"


def test_resume_restores_context_metadata(tmp_path):
    from task_store import SQLiteTaskStore
    store = SQLiteTaskStore(str(tmp_path / "tasks.db"))
    snapshot = {"task_id": "ctx", "status": "FAILED", "goal": "ctx task", "result": None,
                "error": "old", "step": 2, "created_at": 1.0, "updated_at": 1.0,
                "phase": "observing", "plan": "inspect", "latest_tool": "read_file"}
    store.save(snapshot)
    manager = TaskManager(lambda **_: AgentRuntime(lambda _: '{"action":"final","answer":"ok"}', FakeClient()), store=store)
    runtime = manager.get("ctx")
    assert runtime is None
    # resume reconstructs the persisted runtime before executing it
    result = manager.resume("ctx")
    assert result.status == TaskStatus.COMPLETED
