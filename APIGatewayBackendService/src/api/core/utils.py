import os
from typing import Tuple
from .config import settings

ALLOWED_TEXT = {".pdf", ".docx", ".txt"}
ALLOWED_VIDEO = {".mp4", ".avi", ".webm"}
ALLOWED_AUDIO = {".mp3", ".wav", ".aac"}

def validate_and_classify(filename: str) -> Tuple[str, str]:
    ext = os.path.splitext(filename.lower())[1]
    if ext in ALLOWED_TEXT:
        return ("text", ext)
    if ext in ALLOWED_VIDEO:
        return ("video", ext)
    if ext in ALLOWED_AUDIO:
        return ("audio", ext)
    raise ValueError("Unsupported file type")

def storage_path(subdir: str, filename: str) -> str:
    root = settings.storage_root
    path = os.path.join(root, subdir)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)
