"""各省批次控制线（本科线 / 特殊类型招生控制线）。

数据来源：各省教育考试院公布的 2026 年录取控制分数线（公开统计事实）。
用途：给考生直观的"超线多少分"定位，以及本科/专科资格提示。不参与录取概率
计算（那以位次为准），仅作展示与常识兜底。

数据文件 data/control_lines.csv：province,subject_type,year,benke(本科线),tekong(特控线)。
3+3 省份 subject_type 记为"综合"（本科=普通本科/一段线，特控=特殊类型线）。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).resolve().parents[2] / "data" / "control_lines.csv"


@dataclass
class ControlLine:
    province: str
    subject_type: str
    year: int
    benke: int    # 本科批控制线（综合省为本科/一段线）
    tekong: int   # 特殊类型招生控制线（强基/专项/部分一本参考）


@lru_cache(maxsize=1)
def _all() -> list[ControlLine]:
    if not _CSV.exists():
        return []
    out: list[ControlLine] = []
    with _CSV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append(ControlLine(
                    province=r["province"], subject_type=r["subject_type"],
                    year=int(r["year"]), benke=int(r["benke"]), tekong=int(r["tekong"])))
            except (KeyError, ValueError):
                continue
    return out


def lookup(province: str, subject_type: str, year: int | None = None) -> ControlLine | None:
    """取某省某科类的控制线；year 为空时取最新年份。"""
    cands = [c for c in _all() if c.province == province and c.subject_type == subject_type]
    if not cands:
        return None
    if year is not None:
        cands = [c for c in cands if c.year == year] or cands
    return max(cands, key=lambda c: c.year)


def describe(province: str, subject_type: str, score: int) -> str | None:
    """返回一句"超线"定位文案；无该省数据时返回 None。"""
    cl = lookup(province, subject_type)
    if cl is None:
        return None
    if score >= cl.benke:
        over = f"超本科线 {score - cl.benke} 分"
        if score >= cl.tekong:
            return f"✅ {over}，且超特控线 {score - cl.tekong} 分（{cl.year}）"
        return f"✅ {over}（距特控线还差 {cl.tekong - score} 分，{cl.year}）"
    return f"⚠️ 未达本科线（差 {cl.benke - score} 分，{cl.year}）——建议关注专科或复读"


def available_provinces() -> set[str]:
    return {c.province for c in _all()}
