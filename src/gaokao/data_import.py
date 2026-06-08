"""真实数据导入器：把外部 CSV 归一化为系统标准三张表并落盘。

流程：编码鲁棒读取 -> 列名映射（显式 mapping + 常见别名自动识别）-> 填默认值与类型
转换 -> 清洗无法使用的脏行 -> schema 校验 -> 写入目标目录（默认 data/real）。
缺失的兴趣码/热度/就业率等用与生成器一致的口径兜底，缺这些不影响推荐主链路。

命令行：
    python -m gaokao.data_import 院校.csv 专业.csv 录取.csv --out data/real
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .data_schema import (
    CANONICAL_COLUMNS, CATEGORY_RIASEC, DEFAULT_RIASEC, SUBJECT_TYPES,
    ValidationResult, read_rows, validate_dataset,
)

# 常见外部列名 -> 标准列名（小写匹配，去空白）
COMMON_ALIASES: dict[str, str] = {
    "院校id": "id", "学校id": "id", "school_id": "school_id",
    "院校": "name", "院校名称": "name", "学校": "name", "学校名称": "name",
    "专业": "name", "专业名称": "name", "major": "name",
    "省份": "province", "生源省份": "province", "省": "province",
    "城市": "city", "所在城市": "city",
    "层次": "level", "办学层次": "level", "院校层次": "level",
    "类型": "type", "院校类型": "type", "办学类型": "type",
    "门类": "category", "学科门类": "category", "专业门类": "category",
    "专业id": "id", "major_id": "major_id",
    "年份": "year", "录取年份": "year",
    "科类": "subject_type", "选科": "subject_type", "首选科目": "subject_type",
    "最低分": "min_score", "录取最低分": "min_score", "分数": "min_score",
    "最低位次": "min_rank", "位次": "min_rank", "省排名": "min_rank",
    "计划数": "plan_count", "招生计划": "plan_count", "计划人数": "plan_count",
    "就业率": "employment_rate", "热度": "heat", "兴趣码": "riasec_code",
}


@dataclass
class ImportReport:
    ok: bool = False
    out_dir: str = ""
    written: dict[str, int] = field(default_factory=dict)
    dropped: dict[str, int] = field(default_factory=dict)
    validation: ValidationResult | None = None

    def summary(self) -> str:
        parts = [f"写入 {self.out_dir}：" + "、".join(
            f"{k} {v} 行" for k, v in self.written.items())]
        drop = {k: v for k, v in self.dropped.items() if v}
        if drop:
            parts.append("已清洗脏行：" + "、".join(f"{k} {v}" for k, v in drop.items()))
        return "；".join(parts)


def _remap(rows: list[dict], mapping: dict[str, str] | None) -> list[dict]:
    """按显式 mapping + 常见别名，把外部列名改成标准列名。"""
    mapping = mapping or {}
    out: list[dict] = []
    for row in rows:
        new: dict = {}
        for k, v in row.items():
            if k is None:
                continue
            key = mapping.get(k) or COMMON_ALIASES.get(k.strip().lower()) or k.strip()
            new.setdefault(key, v)
        out.append(new)
    return out


def _num(val, cast, default=None):
    try:
        return cast(str(val).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _normalize_schools(rows: list[dict]) -> tuple[list[dict], int]:
    out, dropped = [], 0
    for r in rows:
        if not r.get("id") or not r.get("name"):
            dropped += 1
            continue
        out.append({
            "id": r["id"], "name": r["name"],
            "province": r.get("province", ""), "city": r.get("city", ""),
            "level": r.get("level", "普通"), "type": r.get("type", "综合"),
            "tags": r.get("tags", ""),
        })
    return out, dropped


def _normalize_majors(rows: list[dict]) -> tuple[list[dict], int]:
    out, dropped = [], 0
    for r in rows:
        if not r.get("id") or not r.get("name") or not r.get("school_id"):
            dropped += 1
            continue
        category = r.get("category", "")
        out.append({
            "id": r["id"], "name": r["name"], "category": category,
            "school_id": r["school_id"],
            "riasec_code": r.get("riasec_code") or CATEGORY_RIASEC.get(category, DEFAULT_RIASEC),
            "heat": _num(r.get("heat"), float, 50.0),
            "employment_rate": _num(r.get("employment_rate"), float, 0.85),
            "subject_req": r.get("subject_req", ""),
            "intro": r.get("intro", ""), "core_courses": r.get("core_courses", ""),
            "career_paths": r.get("career_paths", ""),
            "industry_outlook": r.get("industry_outlook", ""),
            "suits": r.get("suits", ""),
        })
    return out, dropped


def _normalize_admissions(
    rows: list[dict], school_ids: set[str], major_ids: set[str]
) -> tuple[list[dict], int]:
    out, dropped = [], 0
    for r in rows:
        score = _num(r.get("min_score"), lambda x: int(float(x)))
        rank = _num(r.get("min_rank"), lambda x: int(float(x)))
        year = _num(r.get("year"), lambda x: int(float(x)))
        plan = _num(r.get("plan_count"), lambda x: int(float(x)), 0)
        subj = r.get("subject_type")
        # 清洗：引用不存在、数值非法、科类未知的行直接丢弃
        if (r.get("school_id") not in school_ids or r.get("major_id") not in major_ids
                or score is None or rank is None or year is None
                or rank <= 0 or subj not in SUBJECT_TYPES):
            dropped += 1
            continue
        out.append({
            "school_id": r["school_id"], "major_id": r["major_id"], "year": year,
            "province": r.get("province", ""), "subject_type": subj,
            "min_score": score, "min_rank": rank, "plan_count": max(plan or 0, 0),
        })
    return out, dropped


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def import_dataset(
    schools_src: str | Path,
    majors_src: str | Path,
    admissions_src: str | Path,
    out_dir: str | Path = "data/real",
    mappings: dict[str, dict[str, str]] | None = None,
) -> ImportReport:
    """读取三份外部 CSV，归一化并校验，成功则写入 out_dir。"""
    mappings = mappings or {}
    schools = _remap(read_rows(schools_src), mappings.get("schools"))
    majors = _remap(read_rows(majors_src), mappings.get("majors"))
    admissions = _remap(read_rows(admissions_src), mappings.get("admissions"))

    schools_n, d_s = _normalize_schools(schools)
    majors_n, d_m = _normalize_majors(majors)
    school_ids = {r["id"] for r in schools_n}
    major_ids = {r["id"] for r in majors_n}
    adm_n, d_a = _normalize_admissions(admissions, school_ids, major_ids)

    report = ImportReport(out_dir=str(out_dir))
    report.dropped = {"schools.csv": d_s, "majors.csv": d_m, "admission_scores.csv": d_a}

    # 先写临时目录校验，通过再落盘，避免污染目标目录
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _write_csv(tmp_path / "schools.csv", schools_n, CANONICAL_COLUMNS["schools.csv"])
        _write_csv(tmp_path / "majors.csv", majors_n, CANONICAL_COLUMNS["majors.csv"])
        _write_csv(tmp_path / "admission_scores.csv", adm_n,
                   CANONICAL_COLUMNS["admission_scores.csv"])
        result = validate_dataset(tmp_path)
        report.validation = result
        if not result.ok:
            return report

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for fname in ("schools.csv", "majors.csv", "admission_scores.csv"):
            (out / fname).write_bytes((tmp_path / fname).read_bytes())

    report.ok = True
    report.written = {
        "schools.csv": len(schools_n), "majors.csv": len(majors_n),
        "admission_scores.csv": len(adm_n)}
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把真实录取数据导入为系统标准数据集")
    ap.add_argument("schools", help="院校 CSV")
    ap.add_argument("majors", help="专业 CSV")
    ap.add_argument("admissions", help="录取记录 CSV")
    ap.add_argument("--out", default="data/real", help="输出目录（默认 data/real）")
    args = ap.parse_args(argv)

    rep = import_dataset(args.schools, args.majors, args.admissions, args.out)
    if rep.ok:
        print("✅ 导入成功：" + rep.summary())
        return 0
    print("❌ 导入失败，未写入。问题如下：")
    for e in (rep.validation.errors if rep.validation else ["未知错误"]):
        print("  -", e)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
