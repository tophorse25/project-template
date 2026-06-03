"""Persistent, accumulating knowledge base for the demand-intelligence engine.

This is the engine's memory. Evidence is keyed by a stable id derived from the
canonical Reddit URL, so re-collecting the same post across runs *accumulates*
(updates ``last_seen`` and appends a ``score_history`` snapshot) instead of
duplicating. That cross-run accumulation is the answer to "the data is not
enough": thin individual crawls compound into a usable signal over time.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, Iterable, TypeVar

from store.models import (
    DemandTheme,
    Evidence,
    PipelineRun,
    ResearchRun,
    ThemeStatus,
    utc_now,
)
from store.schema import SCHEMA

T = TypeVar("T")

DEFAULT_DB_PATH = "data/demand_kb.sqlite3"

# Fields persisted as JSON text, per model.
_JSON_FIELDS: dict[type, set[str]] = {
    Evidence: {"matched_signals", "geo_hints", "score_history", "raw"},
    DemandTheme: {
        "demand_breakdown",
        "pain_breakdown",
        "geo_distribution",
        "current_scores",
        "previous_scores",
        "confidence",
        "aliases",
        "evidence_ids",
        "history",
        "research_history",
    },
    ResearchRun: {
        "input_evidence_ids",
        "findings",
        "scores",
        "geo_analysis",
        "limitations",
        "changed_since_last_run",
    },
    PipelineRun: set(),
}

# String columns that should be re-hydrated into enums on read.
_ENUM_FIELDS: dict[type, dict[str, type]] = {
    DemandTheme: {"status": ThemeStatus},
}


def canonical_url(url: str) -> str:
    """Strip query/fragment/trailing slash so the same thread maps to one id."""

    base = url.split("?")[0].split("#")[0]
    return base.rstrip("/")


def make_evidence_id(url: str, post_id: str | None = None, comment_id: str | None = None) -> str:
    """Stable evidence id. Prefers canonical URL; falls back to post/comment ids."""

    key = canonical_url(url) or f"{post_id or ''}:{comment_id or ''}"
    return "ev_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


class KnowledgeBase:
    """SQLite-backed store for evidence, themes, research runs, and run logs."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def __enter__(self) -> "KnowledgeBase":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ evidence

    def upsert_evidence(self, evidence: Evidence) -> tuple[Evidence, bool]:
        """Insert or accumulate evidence. Returns (stored_evidence, is_new)."""

        existing = self.get_evidence(evidence.evidence_id)
        is_new = existing is None

        if existing is not None:
            evidence.first_seen = existing.first_seen
            history = list(existing.score_history)
            last = history[-1] if history else None
            snapshot = {
                "at": evidence.last_seen,
                "score": evidence.score,
                "comment_count": evidence.comment_count,
            }
            if last is None or (
                last.get("score") != evidence.score
                or last.get("comment_count") != evidence.comment_count
            ):
                history.append(snapshot)
            evidence.score_history = history
        elif not evidence.score_history:
            evidence.score_history = [
                {
                    "at": evidence.first_seen,
                    "score": evidence.score,
                    "comment_count": evidence.comment_count,
                }
            ]

        self._upsert("evidence", "evidence_id", evidence)
        return evidence, is_new

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        row = self.conn.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        return None if row is None else self._from_row(Evidence, row)

    def list_evidence(self, evidence_ids: Iterable[str] | None = None) -> list[Evidence]:
        if evidence_ids is None:
            rows = self.conn.execute(
                "SELECT * FROM evidence ORDER BY created_utc DESC"
            ).fetchall()
            return [self._from_row(Evidence, row) for row in rows]
        ids = list(evidence_ids)
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        rows = self.conn.execute(
            f"SELECT * FROM evidence WHERE evidence_id IN ({placeholders})", ids
        ).fetchall()
        return [self._from_row(Evidence, row) for row in rows]

    def evidence_for_theme(self, theme_id: str) -> list[Evidence]:
        rows = self.conn.execute(
            """
            SELECT e.* FROM evidence e
            JOIN theme_evidence te ON e.evidence_id = te.evidence_id
            WHERE te.theme_id = ?
            ORDER BY e.created_utc DESC
            """,
            (theme_id,),
        ).fetchall()
        return [self._from_row(Evidence, row) for row in rows]

    # -------------------------------------------------------------------- themes

    def upsert_theme(self, theme: DemandTheme) -> None:
        self._upsert("themes", "theme_id", theme)
        self.link_evidence(theme.theme_id, theme.evidence_ids)

    def link_evidence(self, theme_id: str, evidence_ids: Iterable[str]) -> None:
        now = utc_now()
        for evidence_id in evidence_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO theme_evidence (theme_id, evidence_id, linked_at) "
                "VALUES (?, ?, ?)",
                (theme_id, evidence_id, now),
            )
        self.conn.commit()

    def get_theme(self, theme_id: str) -> DemandTheme | None:
        row = self.conn.execute(
            "SELECT * FROM themes WHERE theme_id = ?", (theme_id,)
        ).fetchone()
        return None if row is None else self._from_row(DemandTheme, row)

    def list_themes(
        self,
        statuses: Iterable[str] | None = None,
        product: str | None = None,
    ) -> list[DemandTheme]:
        clauses: list[str] = []
        params: list[Any] = []
        if statuses:
            values = [str(s) for s in statuses]
            clauses.append(f"status IN ({', '.join('?' for _ in values)})")
            params.extend(values)
        if product:
            clauses.append("product = ?")
            params.append(product)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM themes {where} ORDER BY last_seen DESC", params
        ).fetchall()
        return [self._from_row(DemandTheme, row) for row in rows]

    # ------------------------------------------------------------- research runs

    def add_research_run(self, run: ResearchRun) -> None:
        self._upsert("research_runs", "run_id", run)

    def list_research_runs(self, theme_id: str | None = None) -> list[ResearchRun]:
        if theme_id:
            rows = self.conn.execute(
                "SELECT * FROM research_runs WHERE theme_id = ? ORDER BY started_at DESC",
                (theme_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM research_runs ORDER BY started_at DESC"
            ).fetchall()
        return [self._from_row(ResearchRun, row) for row in rows]

    def latest_research_run(self, theme_id: str) -> ResearchRun | None:
        runs = self.list_research_runs(theme_id)
        return runs[0] if runs else None

    # ------------------------------------------------------------- pipeline runs

    def save_pipeline_run(self, run: PipelineRun) -> None:
        self._upsert("pipeline_runs", "pipeline_run_id", run)

    def list_pipeline_runs(self, limit: int = 25) -> list[PipelineRun]:
        rows = self.conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._from_row(PipelineRun, row) for row in rows]

    # ---------------------------------------------------------------- meta/counts

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return default if row is None else row["value"]

    def counts(self) -> dict[str, int]:
        tables = ["evidence", "themes", "theme_evidence", "research_runs", "pipeline_runs"]
        return {
            table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }

    # --------------------------------------------------------------- (de)serialize

    def _upsert(self, table: str, pk: str, item: Any) -> None:
        data = self._to_row(item)
        columns = list(data)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != pk)
        self.conn.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({pk}) DO UPDATE SET {updates}",
            [data[column] for column in columns],
        )
        self.conn.commit()

    def _to_row(self, item: Any) -> dict[str, Any]:
        if not is_dataclass(item):
            raise TypeError("KnowledgeBase persists dataclass instances only")
        json_fields = _JSON_FIELDS.get(type(item), set())
        row = asdict(item)
        for key, value in list(row.items()):
            if key in json_fields:
                row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            elif isinstance(value, ThemeStatus):  # StrEnum is already a str, but be explicit
                row[key] = value.value
        return row

    def _from_row(self, model: type[T], row: sqlite3.Row) -> T:
        data = dict(row)
        json_fields = _JSON_FIELDS.get(model, set())
        enum_fields = _ENUM_FIELDS.get(model, {})
        for name in json_fields:
            if name in data and isinstance(data[name], str):
                data[name] = json.loads(data[name])
        for name, enum_type in enum_fields.items():
            if name in data and data[name] is not None:
                data[name] = enum_type(data[name])
        valid = {field.name for field in fields(model)}
        return model(**{key: value for key, value in data.items() if key in valid})
