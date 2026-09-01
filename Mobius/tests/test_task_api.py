from fastapi.testclient import TestClient
import main


def test_task_api_lifecycle_without_network(monkeypatch):
    class FakeRuntime:
        def __init__(self, **kwargs):
            from runtime import AgentSession, AgentState
            self.session, self.state, self.context = AgentSession(), AgentState(), None
        def run_task(self, question):
            self.state.status = type(self.state.status).COMPLETED
            self.state.result = "done"
            return type("Result", (), {"status": self.state.status})()
        def cancel(self):
            from runtime import TaskStatus
            self.state.status = TaskStatus.CANCELLED

    monkeypatch.setattr(main, "task_manager", main.TaskManager(lambda **_: FakeRuntime()))
    client = TestClient(main.app)
    created = client.post("/tasks", json={"question": "offline"})
    assert created.status_code == 202
    task_id = created.json()["task_id"]
    assert client.get(f"/tasks/{task_id}").status_code == 200
    assert client.post(f"/tasks/{task_id}/cancel").status_code == 200
    assert client.get("/tasks/missing").status_code == 404
