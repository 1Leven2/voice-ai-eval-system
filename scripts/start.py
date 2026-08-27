#!/usr/bin/env python3
"""Non-technical-user launcher: prepare data, start the app, open a browser."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.launcher import build_uvicorn_command, find_free_port, missing_dependencies


def wait_until_ready(url: str, timeout_seconds: float = 12) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.25)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="启动语音智能评测系统")
    parser.add_argument("--port", type=int, default=0, help="指定端口，默认自动选择")
    parser.add_argument("--no-install", action="store_true", help="依赖缺失时不自动安装")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    missing = missing_dependencies()
    if missing:
        if args.no_install:
            print("缺少依赖：" + ", ".join(missing))
            print("请运行：python -m pip install -e .")
            return 2
        print("正在首次安装依赖，请稍候……")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(ROOT)], cwd=ROOT)
        if result.returncode != 0:
            print("依赖安装失败，请检查网络后重试。")
            return result.returncode

    print("正在准备示例数据和真实音频索引……")
    result = subprocess.run([sys.executable, "scripts/run_demo.py"], cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    port = args.port or find_free_port()
    url = f"http://127.0.0.1:{port}/"
    process = subprocess.Popen(build_uvicorn_command(port), cwd=ROOT)
    try:
        if not wait_until_ready(url + "health"):
            print("系统启动超时，请查看终端错误信息。")
            return 1
        print(f"系统已启动：{url}")
        print("关闭当前窗口或按 Ctrl+C 可停止系统。")
        if not args.no_browser:
            webbrowser.open(url)
        process.wait()
        return process.returncode or 0
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
