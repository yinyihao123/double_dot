def test_workspace_tools_are_sandboxed(tmp_path, monkeypatch):
    import tools.workspace as workspace
    monkeypatch.setattr(workspace, "WORKSPACE_ROOT", str(tmp_path))
    assert workspace.write_file("a.txt", "hello")["bytes"] == 5
    assert workspace.read_file("a.txt") == "hello"
    assert "a.txt" in workspace.list_files()
    try:
        workspace.read_file("../outside.txt")
        assert False
    except ValueError:
        pass
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(outside)
    try:
        workspace.read_file("link.txt")
        assert False
    except ValueError:
        pass


def test_workspace_root_is_project_relative_by_default():
    import os
    import tools.workspace as workspace
    assert workspace.WORKSPACE_ROOT.endswith(os.path.join("Mobius", "workspace"))


def test_shell_allowlist_and_no_shell_interpolation(tmp_path, monkeypatch):
    import tools.workspace as workspace
    monkeypatch.setattr(workspace, "WORKSPACE_ROOT", str(tmp_path))
    result = workspace.run_shell(["pwd"])
    assert result["returncode"] == 0 and str(tmp_path) in result["stdout"]
    workspace.write_file("long.txt", "x" * 20)
    output = workspace.run_shell(["cat", "long.txt"], max_output_chars=5)
    assert output["stdout_truncated"] is True and len(output["stdout"]) == 5
    try:
        workspace.run_shell(["sh", "-c", "echo unsafe"])
        assert False
    except ValueError:
        pass


def test_write_file_has_size_limit(tmp_path, monkeypatch):
    import tools.workspace as workspace
    monkeypatch.setattr(workspace, "WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(workspace, "MAX_FILE_BYTES", 4)
    assert workspace.write_file("small.txt", "1234")["bytes"] == 4
    try:
        workspace.write_file("large.txt", "12345")
        assert False
    except ValueError:
        pass


def test_shell_timeout_is_structured(tmp_path, monkeypatch):
    import tools.workspace as workspace
    monkeypatch.setattr(workspace, "WORKSPACE_ROOT", str(tmp_path))
    result = workspace.run_shell(["venv/bin/python", "-m", "pytest", "-q"], timeout=0)
    assert result["timed_out"] is True and result["returncode"] is None


def test_shell_can_use_existing_venv_pytest(tmp_path, monkeypatch):
    import tools.workspace as workspace
    monkeypatch.setattr(workspace, "WORKSPACE_ROOT", str(tmp_path))
    workspace.write_file("test_ok.py", "def test_ok():\n    assert True\n")
    result = workspace.run_shell(["venv/bin/python", "-m", "pytest", "-q"])
    assert result["returncode"] == 0, result
    try:
        workspace.run_shell(["cat", "/etc/passwd"])
        assert False
    except ValueError:
        pass
    try:
        workspace.run_shell(["ls", "../"])
        assert False
    except ValueError:
        pass
