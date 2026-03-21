import os
import uuid
from pathlib import Path
from fastapi import UploadFile

BASE_DIR = Path("storage")


def ensure_storage():
    BASE_DIR.mkdir(exist_ok=True)


async def save_file(file: UploadFile, content: bytes) -> tuple[str, str]:
    ensure_storage()

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"

    file_path = BASE_DIR / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    return file.filename, str(file_path)

async def save_file_stream(file: UploadFile, max_size: int = 25 * 1024 * 1024) -> tuple[str, str]:
    ensure_storage()

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"
    file_path = BASE_DIR / unique_name

    total_size = 0

    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB
            total_size += len(chunk)

            if total_size > max_size:
                f.close()
                os.remove(file_path)
                raise ValueError("File too large")

            f.write(chunk)

    return file.filename, str(file_path)