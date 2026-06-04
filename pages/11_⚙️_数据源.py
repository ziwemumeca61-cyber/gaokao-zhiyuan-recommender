"""数据源：查看当前数据来源（模拟/真实）、校验数据、导入真实录取数据。"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import data_import  # noqa: E402
from gaokao.data_loader import (  # noqa: E402
    REAL_DIR, active_source, available_provinces, data_available,
)
from gaokao.data_schema import CANONICAL_COLUMNS, REQUIRED_COLUMNS, validate_dataset  # noqa: E402
from gaokao.ui_helpers import ensure_data  # noqa: E402

st.set_page_config(page_title="数据源", page_icon="⚙️", layout="wide")
st.title("⚙️ 数据源")
st.caption("系统优先使用导入的真实录取数据；未导入时回退到内置模拟数据用于演示。")

if not ensure_data():
    st.stop()

path, is_real = active_source()

# ---------- 当前来源 ----------
if is_real:
    st.success(f"✅ 当前使用 **真实数据**（{path}）")
else:
    st.info("ℹ️ 当前使用 **模拟数据**（演示用，仅供参考，不代表真实录取结果）。"
            "导入真实数据后将自动切换。")

res = validate_dataset(path)
c1, c2, c3 = st.columns(3)
c1.metric("院校数", res.stats.get("schools.csv", "—"))
c2.metric("专业数", res.stats.get("majors.csv", "—"))
c3.metric("录取记录", res.stats.get("admission_scores.csv", "—"))
st.caption(f"覆盖省份数：{res.stats.get('provinces', '—')}　|　"
           f"校验：{'✅ 通过' if res.ok else '❌ 有问题'}")
if res.errors:
    for e in res.errors:
        st.error(e)
if res.warnings:
    for w in res.warnings:
        st.warning(w)

st.divider()

# ---------- schema 文档 ----------
with st.expander("📐 标准数据格式（导入前请对照）"):
    st.markdown("导入需要三份 CSV（UTF-8 或 GBK 均可）。**必需列**如下，其余为可选：")
    for fname in ("schools.csv", "majors.csv", "admission_scores.csv"):
        req = "、".join(REQUIRED_COLUMNS[fname])
        opt = [c for c in CANONICAL_COLUMNS[fname] if c not in REQUIRED_COLUMNS[fname]]
        st.markdown(f"**{fname}**　必需：`{req}`"
                    + (f"　可选：`{'、'.join(opt)}`" if opt else ""))
    st.markdown(
        "- `subject_type` 取值：**物理 / 历史**；`min_score` 0~750；`min_rank` 为正整数。\n"
        "- 列名可用常见中文（如 院校名称/最低分/位次/科类），导入器会自动识别。\n"
        "- 缺失的兴趣码/热度/就业率会按学科门类自动兜底，不影响推荐。\n"
        "- 也可用命令行：`python -m gaokao.data_import 院校.csv 专业.csv 录取.csv --out data/real`")

# ---------- 上传导入 ----------
st.markdown("#### ⬆️ 导入真实数据")
u1, u2, u3 = st.columns(3)
f_schools = u1.file_uploader("院校 schools.csv", type=["csv"])
f_majors = u2.file_uploader("专业 majors.csv", type=["csv"])
f_adm = u3.file_uploader("录取 admission_scores.csv", type=["csv"])

if st.button("🚀 校验并导入", type="primary",
             disabled=not (f_schools and f_majors and f_adm)):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        paths = {}
        for key, up in (("s", f_schools), ("m", f_majors), ("a", f_adm)):
            p = tmp / f"{key}.csv"
            p.write_bytes(up.getvalue())
            paths[key] = p
        rep = data_import.import_dataset(paths["s"], paths["m"], paths["a"],
                                        out_dir=REAL_DIR)
    if rep.ok:
        st.cache_data.clear()
        st.success("✅ 导入成功！" + rep.summary())
        st.balloons()
        st.rerun()
    else:
        st.error("❌ 导入失败，未改动现有数据。请按下列问题修正后重试：")
        for e in (rep.validation.errors if rep.validation else ["未知错误"]):
            st.markdown(f"- {e}")

# ---------- 停用真实数据 ----------
if is_real:
    st.divider()
    st.markdown("#### 切回模拟数据")
    confirm = st.checkbox("我确认删除已导入的真实数据（可重新导入恢复）")
    if st.button("🗑️ 删除真实数据并切回模拟", disabled=not confirm):
        for fname in ("schools.csv", "majors.csv", "admission_scores.csv"):
            fp = REAL_DIR / fname
            if fp.exists():
                fp.unlink()
        st.cache_data.clear()
        st.success("已删除真实数据，已切回模拟数据。")
        st.rerun()

st.caption(f"可选省份：{', '.join(available_provinces()) if data_available() else '—'}")
