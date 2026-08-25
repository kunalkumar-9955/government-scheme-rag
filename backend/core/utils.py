"""
core/utils.py — Shared utility functions
"""
import uuid
import hashlib
import os
import re
from typing import Optional
from django.conf import settings


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def hash_file(file_obj) -> str:
    """
    Compute SHA-256 hash of an uploaded file for deduplication.
    Resets file pointer after reading.
    """
    sha256 = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(8192), b""):
        sha256.update(chunk)
    file_obj.seek(0)
    return sha256.hexdigest()


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filenames."""
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    filename = re.sub(r"\s+", "_", filename).strip("._")
    return filename or "document"


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is in the allowed list."""
    ext = os.path.splitext(filename)[1].lower()
    allowed = getattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        [".pdf", ".docx", ".doc", ".html", ".htm", ".txt"]
    )
    return ext in allowed


def validate_file_magic(file_obj, filename: str) -> tuple[bool, str]:
    """
    Validate file content magic bytes / signatures against dangerous executables
    and ensure format matches extension.
    Returns (is_valid, error_message).
    """
    file_obj.seek(0)
    header = file_obj.read(1024)
    file_obj.seek(0)

    # 1. Prevent known dangerous executable headers (Windows PE .exe, ELF, Mach-O, scripts)
    if header.startswith(b"MZ"):  # Windows PE executable
        return False, "Dangerous file content detected: Executable binary (MZ header) is not allowed."
    if header.startswith(b"\x7fELF"):  # Linux ELF binary
        return False, "Dangerous file content detected: ELF binary executable is not allowed."
    if header.startswith(b"\xca\xfe\xba\xbe") or header.startswith(b"\xcf\xfa\xed\xfe"):  # Mach-O
        return False, "Dangerous file content detected: Mach-O binary executable is not allowed."
    if header.startswith(b"#!/bin/") or header.startswith(b"#!/usr/bin/"):
        return False, "Dangerous file content detected: Shell scripts are not allowed."

    ext = os.path.splitext(filename)[1].lower()

    # 2. Check PDF signature
    if ext == ".pdf":
        if not header.startswith(b"%PDF-"):
            return False, "Invalid PDF file: Missing %PDF- signature in header."

    # 3. Check DOCX (ZIP archive signature)
    elif ext == ".docx":
        if not header.startswith(b"PK\x03\x04"):
            return False, "Invalid DOCX file: Missing ZIP archive signature in header."

    return True, ""


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def success_response(data=None, message: str = "Success", status_code: int = 200) -> dict:
    """Build a standard success response payload."""
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return payload


def error_response(message: str = "An error occurred", code: str = "ERROR", details=None, status_code: int = 400) -> dict:
    """Build a standard error response payload."""
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count using tiktoken."""
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate
        return len(text.split()) * 4 // 3


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split a list into chunks of size chunk_size."""
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def indian_states() -> list[tuple[str, str]]:
    """Return list of Indian states for profile choices."""
    return [
        ("AN", "Andaman and Nicobar Islands"),
        ("AP", "Andhra Pradesh"),
        ("AR", "Arunachal Pradesh"),
        ("AS", "Assam"),
        ("BR", "Bihar"),
        ("CH", "Chandigarh"),
        ("CT", "Chhattisgarh"),
        ("DN", "Dadra and Nagar Haveli and Daman and Diu"),
        ("DL", "Delhi"),
        ("GA", "Goa"),
        ("GJ", "Gujarat"),
        ("HR", "Haryana"),
        ("HP", "Himachal Pradesh"),
        ("JK", "Jammu and Kashmir"),
        ("JH", "Jharkhand"),
        ("KA", "Karnataka"),
        ("KL", "Kerala"),
        ("LA", "Ladakh"),
        ("LD", "Lakshadweep"),
        ("MP", "Madhya Pradesh"),
        ("MH", "Maharashtra"),
        ("MN", "Manipur"),
        ("ML", "Meghalaya"),
        ("MZ", "Mizoram"),
        ("NL", "Nagaland"),
        ("OD", "Odisha"),
        ("PY", "Puducherry"),
        ("PB", "Punjab"),
        ("RJ", "Rajasthan"),
        ("SK", "Sikkim"),
        ("TN", "Tamil Nadu"),
        ("TG", "Telangana"),
        ("TR", "Tripura"),
        ("UP", "Uttar Pradesh"),
        ("UK", "Uttarakhand"),
        ("WB", "West Bengal"),
    ]
