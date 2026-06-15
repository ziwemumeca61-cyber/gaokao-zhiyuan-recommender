"""我的志愿表：查看 / 调整顺序 / 移除心愿单，并一键导出 Markdown / Word / PDF。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import report  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, get_wishlist, move_wishlist_item, remove_from_wishlist,
    render_major_detail, render_scope_banner, require_student, school_caption,
    wishlist_items,
)

st.title("❤️ 我的志愿表")
st.caption("把心仪的 院校·专业 排好顺序，越靠前优先级越高，最后一键导出。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

items = wishlist_items()

if not items:
    st.info("心愿单还是空的～ 去 **🃏 卡片选校** 或 **🎯 志愿推荐** 把喜欢的专业加进来吧。")
    st.page_link("pages/4_🃏_卡片选校.py", label="➡️ 去卡片选校", icon="🃏")
    st.page_link("pages/3_🎯_志愿推荐.py", label="➡️ 去志愿推荐", icon="🎯")
    st.stop()

st.success(f"心愿单共 {len(items)} 个志愿。可上移/下移调整顺序，或移出。")
if len(items) >= 2:
    st.page_link("pages/9_🆚_院校对比.py", label="🆚 把这些院校放一起对比", icon="🆚")

# ---------- 一键导出 ----------
with st.container(border=True):
    st.markdown("#### 📄 导出志愿表")
    md = report.build_markdown_wishlist(student, items)
    cols = st.columns(4)
    with cols[0]:
        st.download_button("⬇️ Markdown", md, file_name="我的志愿表.md",
                           mime="text/markdown", use_container_width=True)
    with cols[1]:
        if report.docx_available():
            st.download_button(
                "⬇️ Word", report.build_docx_wishlist(student, items),
                file_name="我的志愿表.docx", use_container_width=True,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.button("Word（未安装）", disabled=True, use_container_width=True)
    with cols[2]:
        if report.pdf_available():
            st.download_button(
                "⬇️ PDF", report.build_pdf_wishlist(student, items),
                file_name="我的志愿表.pdf", mime="application/pdf",
                use_container_width=True)
        else:
            st.button("PDF（未安装）", disabled=True, use_container_width=True)
    if not (report.docx_available() and report.pdf_available()):
        st.caption("💡 Word/PDF 导出按钮置灰是因为本机未装导出库。在项目目录执行 "
                   "`pip install -e .`（或 `pip install python-docx reportlab`）后重启即可。")
    with cols[3]:
        with st.popover("👀 预览", use_container_width=True):
            st.markdown(md)

st.divider()

# ---------- 志愿列表（可排序/移除） ----------
total = len(items)
for idx, (school, major) in enumerate(items):
    with st.container(border=True):
        head, ops = st.columns([5, 2])
        with head:
            st.markdown(f"**{idx + 1}. {major.name}**")
            st.caption(school_caption(school) if school else "未知院校")
        with ops:
            b_up, b_down, b_del = st.columns(3)
            if b_up.button("⬆️", key=f"up_{major.id}", disabled=idx == 0,
                           help="上移", use_container_width=True):
                move_wishlist_item(major.id, -1)
                st.rerun()
            if b_down.button("⬇️", key=f"down_{major.id}", disabled=idx == total - 1,
                             help="下移", use_container_width=True):
                move_wishlist_item(major.id, 1)
                st.rerun()
            if b_del.button("🗑️", key=f"del_{major.id}", help="移出心愿单",
                            use_container_width=True):
                remove_from_wishlist(major.id)
                st.rerun()
        with st.expander("📚 这个专业是干嘛的？"):
            render_major_detail(major)

if st.button("🧹 清空心愿单", type="secondary"):
    get_wishlist().clear()
    st.rerun()
