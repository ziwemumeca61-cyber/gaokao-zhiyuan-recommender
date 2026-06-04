"""数据集 schema 定义与校验。

系统内部统一使用三张表（schools / majors / admission_scores）。真实数据接入时，
先归一化到这套"标准列"，再用本模块校验：必需列、类型/取值范围、枚举、引用完整性。
读取对编码鲁棒（真实政务 CSV 常见 GBK/GB18030）。校验只读原始行，不依赖 data_loader，
故对脏数据也不会直接抛错，而是收集成可读的错误/警告清单。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

# ---- 标准列：必需 + 全量（多余列原样保留） ----
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "schools.csv": ["id", "name", "province", "city", "level", "type"],
    "majors.csv": ["id", "name", "category", "school_id"],
    "admission_scores.csv": [
        "school_id", "major_id", "year", "province", "subject_type",
        "min_score", "min_rank", "plan_count"],
}
CANONICAL_COLUMNS: dict[str, list[str]] = {
    "schools.csv": ["id", "name", "province", "city", "level", "type", "tags"],
    "majors.csv": [
        "id", "name", "category", "school_id", "riasec_code", "heat",
        "employment_rate", "intro", "core_courses", "career_paths",
        "industry_outlook", "suits"],
    "admission_scores.csv": [
        "school_id", "major_id", "year", "province", "subject_type",
        "min_score", "min_rank", "plan_count"],
}
DATASET_FILES = tuple(REQUIRED_COLUMNS.keys())

SUBJECT_TYPES = {"物理", "历史"}
SCORE_RANGE = (0, 750)

# 学科门类 -> 默认 RIASEC 主导码（真实专业缺兴趣码时兜底，与生成器口径一致）
CATEGORY_RIASEC: dict[str, str] = {
    "工学": "RI", "理学": "IR", "医学": "IS", "农学": "RI",
    "经济学": "IE", "管理学": "EC", "法学": "SE", "文学": "AS",
    "教育学": "SI", "历史学": "AI", "哲学": "AI", "艺术学": "AE",
}
DEFAULT_RIASEC = "IC"


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def error(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def read_rows(path: str | Path) -> list[dict]:
    """编码鲁棒地读取 CSV 为字典行。依次尝试 utf-8-sig / gb18030 / gbk / latin-1。"""
    path = Path(path)
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            # 去掉表头/字段名的首尾空白
            return [{(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
                     for k, v in row.items()} for row in rows]
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    raise UnicodeDecodeError(  # pragma: no cover - 仅极端编码触发
        "csv", b"", 0, 1, f"无法识别的文件编码：{path}（{last_err}）")


def _to_int(val: str) -> int | None:
    try:
        return int(float(str(val).strip()))
    except (TypeError, ValueError):
        return None


def validate_dataset(data_dir: str | Path) -> ValidationResult:
    """校验某目录下的三张表，返回错误/警告/统计。"""
    base = Path(data_dir)
    res = ValidationResult()

    # 1) 文件存在 + 必需列齐全
    tables: dict[str, list[dict]] = {}
    for fname in DATASET_FILES:
        fpath = base / fname
        if not fpath.exists():
            res.error(f"缺少文件：{fname}")
            continue
        try:
            rows = read_rows(fpath)
        except Exception as e:  # noqa: BLE001
            res.error(f"{fname} 读取失败：{e}")
            continue
        tables[fname] = rows
        res.stats[fname] = len(rows)
        cols = set(rows[0].keys()) if rows else set()
        missing = [c for c in REQUIRED_COLUMNS[fname] if c not in cols]
        if missing:
            res.error(f"{fname} 缺少必需列：{', '.join(missing)}")
        if not rows:
            res.warn(f"{fname} 没有数据行")

    if not res.ok:
        return res  # 结构性问题先返回，避免后续误报

    # 2) 引用完整性 + 取值校验
    school_ids = {r["id"] for r in tables["schools.csv"] if r.get("id")}
    major_ids = {r["id"] for r in tables["majors.csv"] if r.get("id")}

    if len(school_ids) != len(tables["schools.csv"]):
        res.warn("schools.csv 存在空或重复的 id")
    if len(major_ids) != len(tables["majors.csv"]):
        res.warn("majors.csv 存在空或重复的 id")

    bad_major_school = sum(
        1 for r in tables["majors.csv"] if r.get("school_id") not in school_ids)
    if bad_major_school:
        res.error(f"majors.csv 有 {bad_major_school} 行的 school_id 在 schools 中不存在")

    adm = tables["admission_scores.csv"]
    bad_ref = bad_subject = bad_num = 0
    provinces: set[str] = set()
    for r in adm:
        if r.get("school_id") not in school_ids or r.get("major_id") not in major_ids:
            bad_ref += 1
        if r.get("subject_type") not in SUBJECT_TYPES:
            bad_subject += 1
        provinces.add(r.get("province", ""))
        score, rank = _to_int(r.get("min_score")), _to_int(r.get("min_rank"))
        year = _to_int(r.get("year"))
        if (score is None or rank is None or year is None
                or rank <= 0 or not (SCORE_RANGE[0] <= score <= SCORE_RANGE[1])):
            bad_num += 1

    if bad_ref:
        res.error(f"admission_scores.csv 有 {bad_ref} 行引用了不存在的院校/专业")
    if bad_subject:
        res.error(f"admission_scores.csv 有 {bad_subject} 行的科类不是 物理/历史")
    if bad_num:
        res.error(f"admission_scores.csv 有 {bad_num} 行的 分数/位次/年份 非法"
                  f"（分数需 {SCORE_RANGE[0]}~{SCORE_RANGE[1]}、位次>0）")

    res.stats["provinces"] = len([p for p in provinces if p])
    return res
