import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_ROOT = Path(
    os.environ.get("MJK_STORAGE_ROOT", str(BACKEND_DIR / "storage"))
).resolve()
DB_PATH = STORAGE_ROOT / "mjk.db"
PROJECTS_ROOT = STORAGE_ROOT / "projects"


class Storage:
    """Persistent local project metadata + file storage foundation."""

    def __init__(self) -> None:
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    output_type TEXT NOT NULL,
                    style TEXT NOT NULL,
                    language TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    plan_json TEXT,
                    error TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        project_id = uuid.uuid4().hex
        now = self._now()
        project_dir = PROJECTS_ROOT / project_id

        for name in ("director", "scenes", "audio", "captions", "final"):
            (project_dir / name).mkdir(parents=True, exist_ok=True)

        project = {
            "id": project_id,
            "status": "queued",
            "prompt": str(data.get("prompt", "")).strip(),
            "duration_seconds": int(data.get("duration_seconds", 30)),
            "aspect_ratio": str(data.get("aspect_ratio", "16:9")),
            "output_type": str(data.get("output_type", "general")),
            "style": str(data.get("style", "cinematic")),
            "language": str(data.get("language", "فارسی")),
            "created_at": now,
            "updated_at": now,
            "plan": data.get("plan"),
            "error": None,
        }

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects
                (id, status, prompt, duration_seconds, aspect_ratio,
                 output_type, style, language, created_at, updated_at,
                 plan_json, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["id"], project["status"], project["prompt"],
                    project["duration_seconds"], project["aspect_ratio"],
                    project["output_type"], project["style"],
                    project["language"], project["created_at"],
                    project["updated_at"],
                    json.dumps(project["plan"], ensure_ascii=False)
                    if project["plan"] is not None else None,
                    None,
                ),
            )

        if project["plan"] is not None:
            self.write_json(
                project_id,
                "director/plan.json",
                project["plan"],
                "director_plan",
            )

        self.write_json(
            project_id,
            "project.json",
            {
                "id": project_id,
                "status": project["status"],
                "duration_seconds": project["duration_seconds"],
                "aspect_ratio": project["aspect_ratio"],
                "output_type": project["output_type"],
                "style": project["style"],
                "language": project["language"],
                "next_stage": "director" if project["plan"] is None
                else "video_generation",
            },
            "project_manifest",
        )

        return project

    def update_project(
        self,
        project_id: str,
        status: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        fields = ["updated_at = ?"]
        values: List[Any] = [self._now()]

        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if plan is not None:
            fields.append("plan_json = ?")
            values.append(json.dumps(plan, ensure_ascii=False))
        if error is not None:
            fields.append("error = ?")
            values.append(error)

        values.append(project_id)

        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE projects SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            if cur.rowcount == 0:
                raise KeyError("project_not_found")

        if plan is not None:
            self.write_json(
                project_id,
                "director/plan.json",
                plan,
                "director_plan",
            )

        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

        if row is None:
            raise KeyError("project_not_found")

        result = dict(row)
        raw_plan = result.pop("plan_json")
        result["plan"] = json.loads(raw_plan) if raw_plan else None
        result["storage_path"] = str(PROJECTS_ROOT / project_id)

        if result["status"] == "awaiting_video_provider":
            result["next_stage"] = "video_generation"
        elif result["status"] == "completed":
            result["next_stage"] = "download"
        elif result["status"] == "failed":
            result["next_stage"] = "retry"
        else:
            result["next_stage"] = result["status"]

        return result

    def write_json(
        self,
        project_id: str,
        relative_path: str,
        value: Dict[str, Any],
        kind: str,
    ) -> Dict[str, Any]:
        path = self._safe_project_path(project_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            value, ensure_ascii=False, indent=2
        ).encode("utf-8")
        path.write_bytes(payload)
        return self._register_file(
            project_id, relative_path, kind, len(payload)
        )

    def _safe_project_path(
        self, project_id: str, relative_path: str
    ) -> Path:
        root = (PROJECTS_ROOT / project_id).resolve()
        path = (root / relative_path).resolve()

        if root != path and root not in path.parents:
            raise ValueError("invalid_storage_path")

        return path

    def _register_file(
        self,
        project_id: str,
        relative_path: str,
        kind: str,
        size_bytes: int,
    ) -> Dict[str, Any]:
        file_id = uuid.uuid4().hex
        now = self._now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO files
                (id, project_id, relative_path, kind, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id, project_id, relative_path,
                    kind, size_bytes, now
                ),
            )

        return {
            "id": file_id,
            "project_id": project_id,
            "relative_path": relative_path,
            "kind": kind,
            "size_bytes": size_bytes,
            "created_at": now,
        }

    def list_files(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, project_id, relative_path, kind,
                       size_bytes, created_at
                FROM files
                WHERE project_id = ?
                ORDER BY created_at
                """,
                (project_id,),
            ).fetchall()

        return [dict(row) for row in rows]
