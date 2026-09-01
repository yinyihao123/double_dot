import os
import subprocess
from tool_core import Tool

WORKSPACE_ROOT = os.path.abspath(os.getenv(
    "MOBIUS_WORKSPACE_ROOT",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace"),
))
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
ALLOWED_COMMANDS = {"python", "python3", "pytest", "ls", "cat", "pwd"}
MAX_FILE_BYTES = int(os.getenv("MOBIUS_MAX_FILE_BYTES", str(1024 * 1024)))


def _safe_path(path):
    candidate = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if candidate != WORKSPACE_ROOT and not candidate.startswith(WORKSPACE_ROOT + os.sep):
        raise ValueError("path must stay inside workspace")
    # Resolve existing symlinks so a workspace entry cannot point outside it.
    root_real = os.path.realpath(WORKSPACE_ROOT)
    candidate_real = os.path.realpath(candidate)
    if candidate_real != root_real and not candidate_real.startswith(root_real + os.sep):
        raise ValueError("path must stay inside workspace")
    return candidate


def list_files(path="."):
    root = _safe_path(path)
    if not os.path.isdir(root):
        raise ValueError("directory does not exist")
    return sorted(os.listdir(root))


def read_file(path):
    with open(_safe_path(path), "r", encoding="utf-8") as handle:
        return handle.read()


def write_file(path, content):
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    size = len(content.encode("utf-8"))
    if size > MAX_FILE_BYTES:
        raise ValueError(f"content exceeds maximum size ({MAX_FILE_BYTES} bytes)")
    target = _safe_path(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content)
    return {"path": os.path.relpath(target, WORKSPACE_ROOT), "bytes": size}


def run_shell(command, timeout=30, max_output_chars=16384):
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list using an allowed executable")
    executable = command[0]
    if executable in {"venv/bin/python", "venv/bin/python3"}:
        executable = VENV_PYTHON
        command = [executable] + command[1:]
    elif executable not in ALLOWED_COMMANDS:
        raise ValueError("command must be a non-empty list using an allowed executable")
    if executable in {"python", "python3", VENV_PYTHON}:
        if len(command) < 3 or command[1] != "-m" or command[2] != "pytest":
            raise ValueError("python is restricted to: python -m pytest ...")
    for argument in command[1:]:
        if not isinstance(argument, str):
            raise ValueError("command arguments must be strings")
        if argument.startswith("-"):
            continue
        if os.path.isabs(argument) or ".." in argument.replace("\\", "/").split("/"):
            raise ValueError("command path must stay inside workspace")
    try:
        completed = subprocess.run(command, cwd=WORKSPACE_ROOT, capture_output=True,
                                   text=True, timeout=min(float(timeout), 60), shell=False)
    except subprocess.TimeoutExpired as exc:
        return {"returncode": None, "stdout": (exc.stdout or "")[:max_output_chars],
                "stderr": "command timed out", "stdout_truncated": False,
                "stderr_truncated": False, "timed_out": True}
    stdout = completed.stdout
    stderr = completed.stderr
    limit = max(1, int(max_output_chars))
    return {"returncode": completed.returncode,
            "stdout": stdout[:limit], "stderr": stderr[:limit],
            "stdout_truncated": len(stdout) > limit,
            "stderr_truncated": len(stderr) > limit}


tools = [
    Tool("list_files", "列出 workspace 内文件", list_files, {"path": {"type": "string"}}),
    Tool("read_file", "读取 workspace 内文本文件", read_file, {"path": {"type": "string"}}, ["path"]),
    Tool("write_file", "写入 workspace 内文本文件", write_file, {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    Tool("run_shell", "在 workspace 内执行白名单命令", run_shell, {"command": {"type": "array"}, "timeout": {"type": "number"}, "max_output_chars": {"type": "integer"}}, ["command"]),
]
