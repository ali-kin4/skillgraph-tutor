"""Regenerate the README screenshots from the synthetic demo cohort.

Starts the loopback dashboard against a throwaway workspace and captures each view with a
locally installed Chromium-based browser in headless mode. No extra Python packages needed.

    python scripts/capture_screenshots.py            # writes docs/images/*.png
    python scripts/capture_screenshots.py --browser "/path/to/chrome"
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import HTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillgraph_tutor.dashboard_server import make_handler  # noqa: E402
from skillgraph_tutor.demo_data import create_demo_workspace  # noqa: E402

# (file name, view hash, width, height)
SHOTS = [
    ("insights-desktop.png", "insights", 1600, 1720),
    ("overview-desktop.png", "overview", 1440, 1500),
    ("learners-desktop.png", "learners", 1440, 1050),
    ("knowledge-graph-desktop.png", "map", 1440, 1050),
    ("review-center-desktop.png", "reviews", 1440, 1000),
]

CANDIDATES = [
    "chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser(explicit: str | None) -> str:
    for candidate in [explicit] if explicit else CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    raise SystemExit("No Chromium-based browser found; pass --browser /path/to/chrome.")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--browser", help="Path to a Chromium-based browser executable.")
    parser.add_argument("--out", default=str(ROOT / "docs" / "images"))
    args = parser.parse_args()
    browser = find_browser(args.browser)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        workspace = create_demo_workspace(Path(tmp) / "workspace")
        port = free_port()
        server = HTTPServer(("127.0.0.1", port), make_handler(workspace))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        urlopen(f"http://127.0.0.1:{port}/api/dashboard", timeout=10).read()
        try:
            for name, view, width, height in SHOTS:
                target = out / name
                subprocess.run(
                    [
                        browser,
                        "--headless=new",
                        "--disable-gpu",
                        "--hide-scrollbars",
                        "--force-prefers-reduced-motion",
                        "--run-all-compositor-stages-before-draw",
                        "--force-device-scale-factor=1",
                        f"--window-size={width},{height}",
                        "--virtual-time-budget=6000",
                        f"--user-data-dir={Path(tmp) / 'profile'}",
                        f"--screenshot={target}",
                        f"http://127.0.0.1:{port}/#{view}",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=90,
                )
                print(f"captured {target}")
                time.sleep(0.2)
        finally:
            server.shutdown()
    print("Done. Review the images before committing them.")


if __name__ == "__main__":
    main()
