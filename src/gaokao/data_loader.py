"""数据加载层：把 CSV 读成领域对象，并做缓存。

在 Streamlit 环境下用 @st.cache_data 缓存；在纯测试环境下退化为简单的进程级缓存，
因此本模块可脱离 Streamlit 独立使用与测试。
"""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path

from .data_schema import resolve_table
from .models import AdmissionRecord, Major, School

# 默认数据目录：仓库根下的 data/（模拟数据）
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
# 真实数据目录：若存在完整三表则优先使用（被 .gitignore 忽略）
REAL_DIR = DATA_DIR / "real"
_DATASET_FILES = ("schools.csv", "majors.csv", "admission_scores.csv")


def _has_dataset(path: Path) -> bool:
    return all(resolve_table(path, f).exists() for f in _DATASET_FILES)


def resolve_data_dir() -> Path:
    """决定实际数据来源：环境变量 GAOKAO_DATA_DIR > data/real > data/（模拟）。"""
    env = os.environ.get("GAOKAO_DATA_DIR")
    if env and _has_dataset(Path(env)):
        return Path(env)
    if _has_dataset(REAL_DIR):
        return REAL_DIR
    return DATA_DIR


def active_source() -> tuple[Path, bool]:
    """返回 (实际数据目录, 是否为真实数据)。真实=非默认模拟目录。"""
    path = resolve_data_dir()
    return path, path.resolve() != DATA_DIR.resolve()


def _cache(func):
    """优先用 streamlit 缓存，没有则用 lru_cache，保证可独立测试。"""
    try:
        import streamlit as st  # noqa: PLC0415

        return st.cache_data(show_spinner=False)(func)
    except Exception:
        return lru_cache(maxsize=None)(func)


def _read_rows(path: Path) -> list[dict]:
    if str(path).endswith(".gz"):
        import gzip  # noqa: PLC0415

        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@_cache
def load_schools(data_dir: str | None = None) -> dict[str, School]:
    base = Path(data_dir) if data_dir else resolve_data_dir()
    schools: dict[str, School] = {}
    for r in _read_rows(resolve_table(base, "schools.csv")):
        schools[r["id"]] = School(
            id=r["id"], name=r["name"], province=r["province"], city=r["city"],
            level=r["level"], type=r["type"],
            tags=[t for t in r.get("tags", "").split("|") if t],
        )
    return schools


@_cache
def load_majors(data_dir: str | None = None) -> dict[str, Major]:
    base = Path(data_dir) if data_dir else resolve_data_dir()
    majors: dict[str, Major] = {}
    for r in _read_rows(resolve_table(base, "majors.csv")):
        majors[r["id"]] = Major(
            id=r["id"], name=r["name"], category=r["category"],
            school_id=r["school_id"], riasec_code=r["riasec_code"],
            heat=float(r["heat"]), employment_rate=float(r["employment_rate"]),
            subject_req=r.get("subject_req", ""),
            intro=r.get("intro", ""),
            core_courses=[c for c in r.get("core_courses", "").split("|") if c],
            career_paths=[c for c in r.get("career_paths", "").split("|") if c],
            industry_outlook=r.get("industry_outlook", ""),
            suits=r.get("suits", ""),
        )
    return majors


@_cache
def load_admissions(data_dir: str | None = None) -> list[AdmissionRecord]:
    base = Path(data_dir) if data_dir else resolve_data_dir()
    records: list[AdmissionRecord] = []
    for r in _read_rows(resolve_table(base, "admission_scores.csv")):
        records.append(AdmissionRecord(
            school_id=r["school_id"], major_id=r["major_id"], year=int(r["year"]),
            province=r["province"], subject_type=r["subject_type"],
            min_score=int(r["min_score"]), min_rank=int(r["min_rank"]),
            plan_count=int(r["plan_count"]),
        ))
    return records


def data_available(data_dir: str | None = None) -> bool:
    base = Path(data_dir) if data_dir else resolve_data_dir()
    return all(resolve_table(base, f).exists() for f in
               ("schools.csv", "majors.csv", "admission_scores.csv"))


@_cache
def available_provinces(data_dir: str | None = None) -> list[str]:
    return sorted({r.province for r in load_admissions(data_dir)})


@_cache
def available_subjects(province: str, data_dir: str | None = None) -> list[str]:
    """某省份在录取数据中出现的科类（物理/历史/综合）。"""
    subs = {r.subject_type for r in load_admissions(data_dir) if r.province == province}
    order = ["物理", "历史", "综合"]
    return [s for s in order if s in subs] or sorted(subs)


@_cache
def available_categories(data_dir: str | None = None) -> list[str]:
    return sorted({m.category for m in load_majors(data_dir).values()})


@_cache
def available_cities(data_dir: str | None = None) -> list[str]:
    return sorted({s.city for s in load_schools(data_dir).values()})
