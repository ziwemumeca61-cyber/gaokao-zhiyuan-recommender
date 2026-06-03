"""一键导出推荐理由文档。

把考生画像 + 冲稳保志愿表 + 每条志愿的概率/兴趣/综合分/推荐理由整理成文档。
默认输出 Markdown（零依赖）；可选输出 Word/PDF（依赖缺失时自动不可用，由调用方判断）。
"""

from __future__ import annotations

from datetime import date

from .models import TIERS, RIASEC_LABELS, Recommendation, Student


def build_markdown_report(
    student: Student, buckets: dict[str, list[Recommendation]]
) -> str:
    lines: list[str] = []
    lines.append("# 高考志愿推荐报告")
    lines.append("")
    lines.append(f"> 生成日期：{date.today().isoformat()}　|　仅供参考，请结合招生章程谨慎决策")
    lines.append("")

    # 考生信息
    lines.append("## 一、考生画像")
    lines.append("")
    lines.append(f"- 分数：**{student.score}**　位次：**{student.rank}**")
    lines.append(f"- 省份：{student.province}　科类：{student.subject_type}")
    if student.level_pref:
        lines.append(f"- 院校层次偏好：{student.level_pref}")
    if student.city_prefs:
        lines.append(f"- 城市偏好：{', '.join(student.city_prefs)}")
    if student.major_prefs:
        lines.append(f"- 专业门类偏好：{', '.join(student.major_prefs)}")
    if student.has_assessment():
        profile = "　".join(
            f"{RIASEC_LABELS[d]} {v:.2f}" for d, v in student.riasec.items())
        lines.append(f"- 兴趣画像(RIASEC)：{profile}")
    lines.append("")

    # 整体策略
    counts = {t: len(buckets.get(t, [])) for t in TIERS}
    lines.append("## 二、整体策略")
    lines.append("")
    lines.append(f"- 冲 {counts['冲']} 个 / 稳 {counts['稳']} 个 / 保 {counts['保']} 个")
    lines.append("- 建议按'冲稳保'梯度合理搭配，保底志愿务必稳妥，避免滑档。")
    lines.append("")

    # 各档志愿
    lines.append("## 三、志愿推荐明细")
    for tier in TIERS:
        recs = buckets.get(tier, [])
        lines.append("")
        lines.append(f"### {tier}（{len(recs)} 个）")
        if not recs:
            lines.append("")
            lines.append("（暂无）")
            continue
        for i, rec in enumerate(recs, start=1):
            lines.append("")
            lines.append(
                f"**{i}. {rec.school.name} · {rec.major.name}**"
                f"（{rec.school.level}/{rec.school.city}）")
            lines.append(
                f"- 参考位次 {rec.ref_rank}　参考分 {rec.ref_score}　"
                f"录取概率 {rec.probability * 100:.0f}%　综合分 {rec.composite_score:.2f}")
            if rec.major.intro:
                lines.append(f"- 专业简介：{rec.major.intro}")
            if rec.reasons:
                lines.append(f"- 推荐理由：{'；'.join(rec.reasons)}")
    lines.append("")
    return "\n".join(lines)


def docx_available() -> bool:
    try:
        import docx  # noqa: F401, PLC0415

        return True
    except Exception:
        return False


def build_docx_report(student: Student, buckets: dict[str, list[Recommendation]]) -> bytes:
    """生成 Word 文档字节流（需要 python-docx）。"""
    import io  # noqa: PLC0415

    from docx import Document  # noqa: PLC0415

    doc = Document()
    doc.add_heading("高考志愿推荐报告", level=0)
    doc.add_paragraph(f"生成日期：{date.today().isoformat()}（仅供参考）")

    doc.add_heading("考生画像", level=1)
    doc.add_paragraph(f"分数 {student.score} / 位次 {student.rank} / "
                      f"{student.province} / {student.subject_type}")

    for tier in TIERS:
        recs = buckets.get(tier, [])
        doc.add_heading(f"{tier}（{len(recs)} 个）", level=1)
        for i, rec in enumerate(recs, start=1):
            doc.add_heading(f"{i}. {rec.school.name} · {rec.major.name}", level=2)
            doc.add_paragraph(
                f"{rec.school.level}/{rec.school.city}　参考位次 {rec.ref_rank}　"
                f"录取概率 {rec.probability * 100:.0f}%")
            if rec.major.intro:
                doc.add_paragraph(f"专业简介：{rec.major.intro}")
            if rec.reasons:
                doc.add_paragraph("推荐理由：" + "；".join(rec.reasons))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
