import datetime
import os
import psutil

from tool_core import Tool



def get_time():

    return datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )



def get_cpu_usage():

    cpu = psutil.cpu_percent()

    return f"CPU:{cpu}%"



def get_disk_usage():

    disk=psutil.disk_usage('/')

    return f"DISK:{disk.percent}%"


def search_file(keyword: str):
    results = []
    for root, _, files in os.walk("workspace"):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line_no, line in enumerate(handle, 1):
                        if keyword.lower() in line.lower():
                            results.append(f"{path}:{line_no}:{line.strip()}")
            except (OSError, UnicodeDecodeError):
                continue
    return results



tools=[

Tool(
    name="search_file",
    description="搜索workspace目录中的文件内容",
    func=search_file,
    parameters={"keyword": {"type": "string", "description": "搜索关键词"}},
    required=["keyword"]
),


Tool(
    name="get_time",
    description="获取服务器时间",
    func=get_time,
    parameters={}
),


Tool(
    name="get_cpu_usage",
    description="获取CPU使用率",
    func=get_cpu_usage,
    parameters={}
),


Tool(
    name="get_disk_usage",
    description="获取磁盘使用率",
    func=get_disk_usage,
    parameters={}
)


]
