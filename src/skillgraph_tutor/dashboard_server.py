"""Loopback-only SkillGraph Insights dashboard, backed by the existing engine.

No auth is provided. This is a local teaching/analytics demonstration,
not an internet-facing learning management system.
"""

from __future__ import annotations

import json
import math
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .analytics import cohort_csv, dashboard_snapshot, load_cohort
from .scheduler import sm2_update
from .student import load_student, save_student
from .tutors import SocraticTutor

IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


def make_handler(workspace: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        """Only serves known assets and explicitly documented API routes."""

        server_version = "SkillGraphInsights/1.0"

        def log_message(self, format_string: str, *args: object) -> None:
            # Suppress student names, prompts and query parameters in console logs.
            if self.path.startswith("/api/"):
                return
            super().log_message(format_string, *args)

        def _reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict) -> None:
            self._reply(status, json.dumps(data, allow_nan=False).encode(), "application/json")

        def _error(self, status: int, reason: str) -> None:
            self._json(status, {"error": reason})

        def _snapshot(self) -> dict:
            graph, students, metadata = load_cohort(workspace)
            return dashboard_snapshot(graph, students, metadata)

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            path = parsed.path
            if path in ASSETS:
                name, kind = ASSETS[path]
                content = (Path(__file__).with_name("web") / name).read_bytes()
                self._reply(HTTPStatus.OK, content, kind)
                return
            if path == "/api/dashboard":
                try:
                    self._json(HTTPStatus.OK, self._snapshot())
                except (OSError, ValueError, KeyError, TypeError):
                    self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to read cohort data.")
                return
            if path == "/api/export.csv":
                try:
                    content = cohort_csv(self._snapshot()).encode("utf-8-sig")
                except (OSError, ValueError, KeyError, TypeError):
                    self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Export could not be generated.")
                    return
                self._reply(HTTPStatus.OK, content, "text/csv; charset=utf-8")
                return
            if path == "/api/export.json":
                try:
                    self._json(HTTPStatus.OK, self._snapshot())
                except (OSError, ValueError, KeyError, TypeError):
                    self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Export could not be generated.")
                return
            if path == "/api/student":
                values = parse_qs(parsed.query).get("id", [])
                student_id = values[0] if len(values) == 1 else ""
                if not IDENTIFIER.fullmatch(student_id):
                    self._error(HTTPStatus.BAD_REQUEST, "Invalid learner ID.")
                    return
                try:
                    snapshot = self._snapshot()
                except (OSError, ValueError, KeyError, TypeError):
                    self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to read cohort data.")
                    return
                student = next((s for s in snapshot["students"] if s["id"] == student_id), None)
                if student is None:
                    self._error(HTTPStatus.NOT_FOUND, "Learner not found.")
                else:
                    self._json(HTTPStatus.OK, student)
                return
            self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

        def _request_data(self) -> dict | None:
            origin = self.headers.get("Origin")
            if origin:
                local = urlsplit(origin)
                host = self.headers.get("Host") or ""
                if local.scheme != "http" or local.netloc != host:
                    self._error(HTTPStatus.FORBIDDEN, "Cross-origin changes are not allowed.")
                    return None
            if self.headers.get_content_type() != "application/json":
                self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Expected application/json.")
                return None
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 8192:
                self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid request size.")
                return None
            try:
                payload = json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._error(HTTPStatus.BAD_REQUEST, "Invalid JSON body.")
                return None
            if not isinstance(payload, dict):
                self._error(HTTPStatus.BAD_REQUEST, "Expected a JSON object.")
                return None
            return payload

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path not in ("/api/attempt", "/api/tutor"):
                self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint.")
                return
            data = self._request_data()
            if data is None:
                return
            student_id = data.get("studentId")
            concept = data.get("concept")
            if (
                not isinstance(student_id, str)
                or not IDENTIFIER.fullmatch(student_id)
                or not isinstance(concept, str)
                or len(concept) > 120
            ):
                self._error(HTTPStatus.BAD_REQUEST, "Invalid learner or concept.")
                return
            try:
                graph, students, metadata = load_cohort(workspace)
            except (OSError, ValueError, TypeError, KeyError):
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Could not read learning data.")
                return
            if concept not in graph.nodes or student_id not in {
                student.student_id for student in students
            }:
                self._error(HTTPStatus.NOT_FOUND, "Unknown learner or concept.")
                return
            if path == "/api/tutor":
                response = data.get("response", "")
                if not isinstance(response, str) or len(response) > 1500:
                    self._error(HTTPStatus.BAD_REQUEST, "Response is too long.")
                    return
                turn = SocraticTutor().teach(concept=concept, response=response)
                self._json(
                    HTTPStatus.OK,
                    {
                        "type": "template-guided",
                        "question": turn.question,
                        "hint": turn.hint,
                        "check": turn.check,
                        "microActions": turn.micro_actions,
                        "disclosure": "Deterministic Socratic templates; no LLM or AI grading.",
                    },
                )
                return
            correct = data.get("correct")
            confidence = data.get("confidence")
            if (
                not isinstance(correct, bool)
                or isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence)
                or not 0 <= confidence <= 1
            ):
                self._error(HTTPStatus.BAD_REQUEST, "Use correct=true/false, confidence 0–1.")
                return
            student_path = workspace / "students" / (student_id + ".json")
            if student_path.is_symlink():
                self._error(HTTPStatus.FORBIDDEN, "Unsafe learner path.")
                return
            try:
                student = load_student(student_path)
                before = student.concept(concept).mastery
                after = student.update_mastery(concept, correct, float(confidence))
                sm2_update(student.concept(concept), quality=4 if correct else 2)
                save_student(student_path, student)
            except (OSError, ValueError, TypeError):
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to save assessment.")
                return
            self._json(
                HTTPStatus.OK,
                {
                    "studentId": student_id,
                    "concept": concept,
                    "before": round(before, 4),
                    "after": round(after, 4),
                    "dueAt": student.concept(concept).reviews.due_at,
                    "synthetic": bool(metadata.get("synthetic")),
                    "disclosure": "Self-reported practice outcome; no independent verification.",
                },
            )

    return DashboardHandler


def run_dashboard(workspace: str | Path, port: int = 8765) -> None:
    """Serve strictly on loopback. Do not expose on a public network."""
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port in 1024–65535.")
    root = Path(workspace).resolve()
    if not (root / "graph.json").is_file():
        raise FileNotFoundError(f"No initialized graph found in {root}")
    server = HTTPServer(("127.0.0.1", port), make_handler(root))
    print(f"SkillGraph Insights: http://127.0.0.1:{port}")
    print(f"Workspace: {root}")
    print("Local demonstration only; no authentication or production deployment.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nClosing SkillGraph Insights.")
    finally:
        server.server_close()
