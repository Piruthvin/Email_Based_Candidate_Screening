import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/reports", tags=["Reports Download"])


@router.get("/download/{filename}", summary="Download Generated Report")
async def download_report(filename: str):
    # Filename safety - prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid report filename")

    base_dir = os.path.abspath(os.path.join("tmp", "reports"))
    file_path = os.path.abspath(os.path.join(base_dir, filename))

    # Ensure canonical path stays strictly inside base_dir
    if not file_path.startswith(base_dir + os.sep) and file_path != base_dir:
        raise HTTPException(status_code=400, detail="Invalid report filename")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
