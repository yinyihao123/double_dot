import datetime
import psutil
import os
from tool_result import success, failure
from tool_registry import Tool

def search_file(keyword: str):
    """
    搜索workspace目录中的文件
    """

    results = []

    for root, dirs, files in os.walk("workspace"):

        for file in files:

            path = os.path.join(root, file)

            with open(path, "r", encoding="utf-8") as f:

                for line_no, line in enumerate(f, 1):

                    if keyword.lower() in line.lower():

                        results.append(
                            f"{path}:{line_no}:{line.strip()}"
                        )


    if not results:
        return success([])


    return success(results)

def get_time():
    """
    获取当前服务器时间
    """

    return datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

def get_cpu_usage():
    """
    获取CPU使用率
    """

    cpu = psutil.cpu_percent(interval=1)

    return f"当前CPU使用率：{cpu}%"

def get_disk_usage():
    """
    获取磁盘使用率
    """

    disk = psutil.disk_usage('/')

    return f"磁盘使用率：{disk.percent}%"


TOOLS = {

    "search_file": Tool(
        name="search_file",
        description="搜索workspace目录中的文件内容",
        func=search_file,
        parameters={
            "keyword":{
                "type":"string",
                "description":"搜索关键词"
            }
        },
        required=[
            "keyword"
        ]
    ),

    "get_time": Tool(
        name="get_time",
        description="获取当前服务器时间",
        func=get_time,
        parameters={}
    ),

    "get_cpu_usage": Tool(
        name="get_cpu_usage",
        description="获取服务器CPU使用率",
        func=get_cpu_usage,
        parameters={}
    ),

    "get_disk_usage": Tool(
        name="get_disk_usage",
        description="获取服务器磁盘使用率",
        func=get_disk_usage,
        parameters={}
    )
}


TOOL_DESCRIPTIONS = [
    tool.schema()
    for tool in TOOLS.values()
]
