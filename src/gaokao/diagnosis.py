"""志愿诊断：把考生的意向志愿（心愿单）整体体检，给出合理化建议。

纯函数实现（不依赖 Streamlit），供「🩺 志愿诊断」页与导出文档（report.py）共用，
保证界面与文档口径一致。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import electives as el
from .data_loader import load_admissions
from .models import Major, School, Student
from .recommender import ml_model, rank_based
from .recommender.history import aggregate


@dataclass
class ItemDiag:
    """单条意向志愿的体检结果。"""

    name: str            # 院校·专业
    has_data: bool       # 是否查到该省份科类的录取数据
    ok_subject: bool     # 选科是否匹配
    tier: str            # 冲/稳/保 / 区间外 / —
    prob: float          # 录取概率（无数据为 0）
    ref_rank: int        # 参考位次（无数据为 0）
    req_label: str       # 选科要求文字

    @property
    def status(self) -> str:
        if not self.ok_subject:
            return "⛔不符选科"
        if not self.has_data:
            return "⚠️无数据"
        return "✅"


@dataclass
class Diagnosis:
    """整份意向志愿的体检结论。"""

    items: list[ItemDiag] = field(default_factory=list)
    findings: list[tuple[str, str]] = field(default_factory=list)  # (severity, text)

    @property
    def count(self) -> int:
        return len(self.items)


def diagnose(student: Student, items: list[tuple[School | None, Major]]) -> Diagnosis:
    """对意向志愿逐项测算并汇总诊断建议。

    severity 取值：error / warning / info / success，调用方据此选择展示样式。
    """
    stats = aggregate(load_admissions(), student.province, student.subject_type)

    diag = Diagnosis()
    for school, major in items:
        ok = el.satisfies(major.subject_req, student.electives)
        stat = stats.get((school.id, major.id)) if school else None
        sname = school.name if school else "未知院校"
        req = el.requirement_label(major.subject_req)
        if stat:
            p, _lo, _hi = ml_model.predict_interval(
                student.rank, stat.ref_rank, stat.trend, rank_cv=stat.rank_cv,
                years=stat.years, plan=stat.total_plan, plan_ratio=stat.plan_ratio)
            tier = rank_based.classify(student.rank, stat.ref_rank) or "区间外"
            diag.items.append(ItemDiag(
                name=f"{sname}·{major.name}", has_data=True, ok_subject=ok,
                tier=tier, prob=p, ref_rank=stat.ref_rank, req_label=req))
        else:
            diag.items.append(ItemDiag(
                name=f"{sname}·{major.name}", has_data=False, ok_subject=ok,
                tier="—", prob=0.0, ref_rank=0, req_label=req))

    diag.findings = _findings(student, items, diag.items)
    return diag


def _findings(
    student: Student,
    items: list[tuple[School | None, Major]],
    evals: list[ItemDiag],
) -> list[tuple[str, str]]:
    data_ev = [e for e in evals if e.has_data]
    n_chong = sum(1 for e in data_ev if e.tier in ("冲", "区间外"))
    n_safe = sum(1 for e in data_ev if e.prob >= 0.8)
    n_low = sum(1 for e in data_ev if e.prob < 0.10)
    n_subj = sum(1 for e in evals if not e.ok_subject)
    n_nodata = sum(1 for e in evals if not e.has_data)
    seen = Counter((s.id if s else "", m.id) for s, m in items)
    n_dup = sum(1 for v in seen.values() if v > 1)

    out: list[tuple[str, str]] = []
    if n_subj:
        out.append(("error",
                    f"⛔ 有 {n_subj} 个不符合你的选科要求，无法填报，请移除或替换。"))
    if n_nodata:
        out.append(("warning",
                    f"⚠️ 有 {n_nodata} 个在「{student.province}·{student.subject_type}」下"
                    "查不到录取数据，可能省份/科类不符或为新增专业，请核实。"))
    if n_dup:
        out.append(("warning", f"🔁 有 {n_dup} 组重复志愿，建议去重。"))
    if n_low:
        out.append(("error",
                    f"🔴 有 {n_low} 个录取概率很低（<10%），基本够不着，建议替换为更稳的。"))
    if n_safe < 2:
        out.append(("warning",
                    f"🛡️ 保底偏少（把握≥80% 的只有 {n_safe} 个），"
                    "建议再补 2~3 个稳妥志愿，谨防滑档。"))
    if n_chong == 0 and len(data_ev) >= 3:
        out.append(("info",
                    "🚀 你的意向全是稳/保，在保底充足的前提下，可适当加 1~2 个冲一冲的好学校。"))
    if not out:
        out.append(("success",
                    "✅ 你的意向志愿梯度合理、保底充足、选科匹配，整体不错！"
                    "建议按冲→稳→保的顺序排好。"))
    return out
