from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.dependencies import logs_service

logs_router = APIRouter(prefix="/logs", tags=["logs"])


@logs_router.get("/file")
async def get_logs_file():
    """
    Get service logs as file
    """
    try:
        logs_service.check_file()
        return FileResponse(logs_service.logs_file_path, filename="idu_bot.log")
    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e)) from e


@logs_router.get("/log")
async def get_logs(length: int):
    """
    Get service logs by length
    """

    try:
        return logs_service.get_logs(length)
    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e)) from e
