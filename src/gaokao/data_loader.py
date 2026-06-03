"""数据加载层：把 CSV 读成领域对象，并做缓存。

在 Streamlit 环境下用 @st.cache_data 缓存；在纯测试环境下退化为简单的进程级缓存，
因此本模块可脱离 Streamlit 独立使用与测试。
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .models import AdmissionRecord, Major, School

# 默认数据目录：仓库根下的 data/
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _cache(func):
    """优先用 streamlit 缓存，没有则用 lru_cache，保证可独立测试。"""
    try:
        import streamlit as st  # noqa: PLC0415

        return st.cache_data(show_spinner=False)(func)
    except Exception:
        return lru_cache(maxsize=None)(func)


def _read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@_cache
def load_schools(data_dir: str | None = None) -> dict[str, School]:
    base = Path(data_dir) if data_dir else DATA_DIR
    schools: dict[str, School] = {}
    for r in _read_rows(base / "schools.csv"):
        schools[r["id"]] = School(
            id=r["id"], name=r["name"], province=r["province"], city=r["city"],
            level=r["level"], type=r["type"],
            tags=[t for t in r.get("tags", "").split("|") if t],
        )
    return schools


@_cache
def load_majors(data_dir: str | None = None) -> dict[str, Major]:
    base = Path(data_dir) if data_dir else DATA_DIR
    majors: dict[str, Major] = {}
    for r in _read_rows(base / "majors.csv"):
        majors[r["id"]] = Major(
            id=r["id"], name=r["name"], category=r["category"],
            school_id=r["school_id"], riasec_code=r["riasec_code"],
            heat=float(r["heat"]), employment_rate=float(r["employment_rate"]),
            intro=r.get("intro", ""),
            core_courses=[c for c in r.get("core_courses", "").split("|") if c],
            career_paths=[c for c in r.get("career_paths", "").split("|") if c],
            industry_outlook=r.get("industry_outlook", ""),
            suits=r.get("suits", ""),
        )
    return majors


@_cache
def load_admissions(data_dir: str | None = None) -> list[AdmissionRecord]:
    base = Path(data_dir) if data_dir else DATA_DIR
    records: list[AdmissionRecord] = []
    for r in _read_rows(base / "admission_scores.csv"):
        records.append(AdmissionRecord(
            school_id=r["school_id"], major_id=r["major_id"], year=int(r["year"]),
            province=r["province"], subject_type=r["subject_type"],
            min_score=int(r["min_score"]), min_rank=int(r["min_rank"]),
            plan_count=int(r["plan_count"]),
        ))
    return records


def data_available(data_dir: str | None = None) -> bool:
    base = Path(data_dir) if data_dir else DATA_DIR
    return all((base / f).exists() for f in
               ("schools.csv", "majors.csv", "admission_scores.csv"))


@_cache
def available_provinces(data_dir: str | None = None) -> list[str]:
    return sorted({r.province for r in load_admissions(data_dir)})


@_cache
def available_categories(data_dir: str | None = None) -> list[str]:
    return sorted({m.category for m in load_majors(data_dir).values()})


@_cache
def available_cities(data_dir: str | None = None) -> list[str]:
    return sorted({s.city for s in load_schools(data_dir).values()})
