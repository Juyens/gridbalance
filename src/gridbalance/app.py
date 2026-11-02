"""Desktop window that hosts the Vue frontend through pywebview."""

import argparse
import sys
from pathlib import Path

import webview

from gridbalance.api import Api

DEV_SERVER_URL = "http://localhost:5173"
REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_BUILD = REPO_ROOT / "frontend" / "dist" / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(prog="gridbalance")
    parser.add_argument(
        "--dev",
        action="store_true",
        help=f"load the Vite dev server at {DEV_SERVER_URL} instead of the build",
    )
    args = parser.parse_args()

    if args.dev:
        url = DEV_SERVER_URL
    elif FRONTEND_BUILD.exists():
        url = str(FRONTEND_BUILD)
    else:
        sys.exit(
            "Frontend build not found: run 'npm run build' in frontend/ or use --dev."
        )

    webview.create_window("GridBalance", url, js_api=Api(), width=1280, height=800)
    webview.start(debug=args.dev)
