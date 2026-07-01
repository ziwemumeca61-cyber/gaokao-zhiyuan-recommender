"""推荐准确度回测（留出法）：用历史年份预测最近一年，量化位次线与录取概率的准确度。

把核心逻辑放在库里，供 scripts/backtest.py 打印、tests/ 做精度回归守门复用。
"""

from __future__ import annotations

from collections import defaultdict

from ..data_loader import load_admissions, load_admissions_for
from . import ml_model
from .history import aggregate

TEST_YEAR = 2025
_FACTORS = (0.55, 0.7, 0.85, 1.0, 1.2, 1.5, 1.9)


def _groups(provinces: list[str] | None, data_dir: str | None):
    """按 (校,专,省,科) 汇总 {年: 记录}。指定省份时只读这些省（快、供测试）。"""
    grouped: dict[tuple, dict[int, object]] = defaultdict(dict)
    if provinces:
        for prov in provinces:
            for subj in ("物理", "历史", "综合"):
                for r in load_admissions_for(prov, subj, data_dir):
                    grouped[(r.school_id, r.major_id, r.province, r.subject_type)][r.year] = r
    else:
        for r in load_admissions(data_dir):
            grouped[(r.school_id, r.major_id, r.province, r.subject_type)][r.year] = r
    return grouped


def run_backtest(
    provinces: list[str] | None = None, data_dir: str | None = None
) -> dict:
    """返回准确度指标。仅用 <TEST_YEAR 的记录预测 TEST_YEAR，与真实值对比。

    指标：n_groups、line_median_rel（位次相对误差中位数）、line_within10/20、
    line_bias、calib_error（概率十分箱平均校准误差）、brier，以及 buckets 明细。
    """
    grouped = _groups(provinces, data_dir)
    rel_errs: list[float] = []
    buckets: dict[int, list[float]] = defaultdict(lambda: [0, 0.0, 0])  # n, Σp, Σ命中
    brier = 0.0
    n_calib = 0
    n_groups = 0

    for (sid, mid, prov, subj), by_year in grouped.items():
        actual = by_year.get(TEST_YEAR)
        prior = [rec for y, rec in by_year.items() if y < TEST_YEAR]
        if actual is None or actual.min_rank <= 0 or len(prior) < 2:
            continue
        stat = aggregate(prior, prov, subj).get((sid, mid))
        if stat is None or stat.ref_rank <= 0:
            continue
        n_groups += 1

        pred = ml_model._proj_ref(stat.ref_rank, stat.plan_ratio)
        rel_errs.append((pred - actual.min_rank) / actual.min_rank)

        for f in _FACTORS:
            cand = max(1, round(stat.ref_rank * f))
            p = ml_model.predict_interval(
                cand, stat.ref_rank, trend=stat.trend, rank_cv=stat.rank_cv,
                years=stat.years, plan=stat.total_plan, plan_ratio=stat.plan_ratio)[0]
            admitted = 1 if cand <= actual.min_rank else 0
            bk = buckets[min(9, int(p * 10))]
            bk[0] += 1
            bk[1] += p
            bk[2] += admitted
            brier += (p - admitted) ** 2
            n_calib += 1

    if not rel_errs or n_calib == 0:
        return {"n_groups": n_groups, "n_calib": n_calib}

    abs_errs = sorted(abs(e) for e in rel_errs)
    n = len(abs_errs)
    calib_error = sum(abs(b[1] / b[0] - b[2] / b[0]) * b[0]
                      for b in buckets.values()) / n_calib
    return {
        "n_groups": n_groups,
        "n_calib": n_calib,
        "line_median_rel": abs_errs[n // 2],
        "line_within10": sum(1 for e in abs_errs if e <= 0.10) / n,
        "line_within20": sum(1 for e in abs_errs if e <= 0.20) / n,
        "line_bias": sum(rel_errs) / n,
        "calib_error": calib_error,
        "brier": brier / n_calib,
        "buckets": {b: (v[0], v[1] / v[0], v[2] / v[0]) for b, v in sorted(buckets.items())},
    }
