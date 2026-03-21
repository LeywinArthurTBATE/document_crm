import os
import uuid
from pathlib import Path
from fastapi import UploadFile

BASE_DIR = Path("storage")


def ensure_storage():
    BASE_DIR.mkdir(exist_ok=True)


async def save_file(file: UploadFile) -> tuple[str, str]:
    """
    return: (file_name, file_path)
    """

    ensure_storage()

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"

    file_path = BASE_DIR / unique_name

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return file.filename, str(file_path)