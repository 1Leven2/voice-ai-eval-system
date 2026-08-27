from __future__ import annotations

import socket
import sys


def build_uvicorn_command(port: int) -> list[str]:
    return [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]


def find_free_port(start: int = 8000, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"无法在 {start}-{start + attempts - 1} 找到可用端口")


def missing_dependencies() -> list[str]:
    modules = {"fastapi": "fastapi", "uvicorn": "uvicorn", "jinja2": "jinja2", "multipart": "python-multipart"}
    missing: list[str] = []
    for module, package in modules.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing
