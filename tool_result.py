from typing import Any


def success(data: Any):

    return {
        "success": True,
        "data": data,
        "error": None
    }



def failure(error: str):

    return {
        "success": False,
        "data": None,
        "error": error
    }