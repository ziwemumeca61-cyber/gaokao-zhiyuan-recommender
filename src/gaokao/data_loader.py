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


def _open_text(path: Path):
    """按扩展名透明地打开纯文本或 .gz。"""
    if str(path).endswith(".gz"):
        import gzip  # noqa: PLC0415

        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


# admission_scores.csv 列序（与 scripts/import_*.py 写出的顺序一致）：
# school_id, major_id, year, province, subject_type, min_score, min_rank, plan_count
def _row_to_admission(r: list[str]) -> AdmissionRecord:
    return AdmissionRecord(
        school_id=r[0], major_id=r[1], year=int(r[2]), province=r[3],
        subject_type=r[4], min_score=int(r[5]), min_rank=int(r[6]),
        plan_count=int(r[7]),
    )


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
    """全量录取记录。数据已达数百万条，用 csv.reader + 位置解析以降低开销；
    只需单省时请改用 load_admissions_for，避免构建整表对象。"""
    base = Path(data_dir) if data_dir else resolve_data_dir()
    with _open_text(resolve_table(base, "admission_scores.csv")) as f:
        rd = csv.reader(f)
        next(rd, None)  # 跳过表头
        return [_row_to_admission(r) for r in rd if r]


@_cache
def load_admissions_for(
    province: str, subject_type: str, data_dir: str | None = None
) -> list[AdmissionRecord]:
    """只加载某省某科类的录取记录（推荐/诊断/对比只关心一个省，避免整表构建）。

    仍需顺序扫描文件，但只为命中的行建对象，比 load_admissions 快数倍且省内存；
    结果按 (省,科类) 缓存，重复调用即时返回。"""
    base = Path(data_dir) if data_dir else resolve_data_dir()
    with _open_text(resolve_table(base, "admission_scores.csv")) as f:
        rd = csv.reader(f)
        next(rd, None)
        return [_row_to_admission(r) for r in rd
                if r and r[3] == province and r[4] == subject_type]


_META_FILE = "admissions_meta.json"


def _scan_admission_meta(base: Path) -> tuple[int, dict[str, list[str]]]:
    """扫描 admission_scores 求 (总行数, {省: [科类...]})；只读列、不建对象。"""
    total = 0
    prov_subj: dict[str, set[str]] = {}
    with _open_text(resolve_table(base, "admission_scores.csv")) as f:
        rd = csv.reader(f)
        next(rd, None)
        for r in rd:
            if not r:
                continue
            total += 1
            prov_subj.setdefault(r[3], set()).add(r[4])
    return total, {p: sorted(s) for p, s in prov_subj.items()}


def write_admission_meta(data_dir: str | None = None) -> Path:
    """把 (总数, 省→科类) 预计算到 admissions_meta.json，供首页/下拉秒开。
    导入脚本改动录取数据后应调用本函数刷新。"""
    import json  # noqa: PLC0415

    base = Path(data_dir) if data_dir else resolve_data_dir()
    total, prov_subj = _scan_admission_meta(base)
    out = base / _META_FILE
    out.write_text(json.dumps({"total": total, "provinces": prov_subj},
                              ensure_ascii=False), encoding="utf-8")
    return out


@_cache
def _admission_meta(data_dir: str | None = None) -> tuple[int, dict[str, list[str]]]:
    """返回 (总行数, {省: [科类...]})。优先读预计算的 admissions_meta.json（秒级），
    缺失时回退到扫描整表，保证无 meta 文件也能工作。"""
    base = Path(data_dir) if data_dir else resolve_data_dir()
    meta_path = base / _META_FILE
    if meta_path.exists():
        import json  # noqa: PLC0415

        try:
            d = json.loads(meta_path.read_text(encoding="utf-8"))
            return int(d["total"]), {p: list(s) for p, s in d["provinces"].items()}
        except Exception:  # noqa: BLE001 — 损坏则回退扫描
            pass
    return _scan_admission_meta(base)


def admission_count(data_dir: str | None = None) -> int:
    """录取记录总数（走轻量元数据，不构建整表对象）。"""
    return _admission_meta(data_dir)[0]


def data_available(data_dir: str | None = None) -> bool:
    base = Path(data_dir) if data_dir else resolve_data_dir()
    return all(resolve_table(base, f).exists() for f in
               ("schools.csv", "majors.csv", "admission_scores.csv"))


@_cache
def available_provinces(data_dir: str | None = None) -> list[str]:
    return sorted(_admission_meta(data_dir)[1])


@_cache
def available_subjects(province: str, data_dir: str | None = None) -> list[str]:
    """某省份在录取数据中出现的科类（物理/历史/综合）。"""
    subs = set(_admission_meta(data_dir)[1].get(province, []))
    order = ["物理", "历史", "综合"]
    return [s for s in order if s in subs] or sorted(subs)


@_cache
def available_categories(data_dir: str | None = None) -> list[str]:
    return sorted({m.category for m in load_majors(data_dir).values()})


@_cache
def available_cities(data_dir: str | None = None) -> list[str]:
    return sorted({s.city for s in load_schools(data_dir).values()})
