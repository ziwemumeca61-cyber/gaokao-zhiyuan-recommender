# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gaokao-zhiyuan-recommender` — 基于多维数据分析与推荐算法的高考志愿填报辅助系统，支持分数线预测与个性化志愿推荐.

A Gaokao (China's college entrance exam) application-form (志愿) assistant built as a
**Streamlit** multi-page app. It helps a student get admitted to schools/majors they
like or are suited for, and makes the process fun and understandable.

## Commands

```bash
# 安装（含开发依赖）
pip install -e ".[dev]"          # 可选导出 Word/PDF：pip install -e ".[dev,export]"

# 生成模拟数据（首次运行或修改生成逻辑后）；应用启动时也会自动生成缺失数据
python data/generate_mock_data.py

# 启动应用
streamlit run app.py

# 测试
pytest -q                                  # 全部
pytest tests/test_rank_based.py -v         # 单个文件
pytest tests/test_engine.py::test_engine_returns_all_tiers -v   # 单个用例

# Lint
ruff check .
```

Python ≥ 3.10. 包通过 `pyproject.toml` 的 `[tool.setuptools] src layout` 暴露为
`gaokao`，并通过 `pythonpath = ["src"]` 让 pytest 直接 import。

## Architecture

三层结构：**核心算法库**（`src/gaokao/`）+ **Streamlit 多页面前端**（`pages/`）+
**模拟数据**（`data/`）。算法与 UI 解耦——所有页面只调用 `gaokao.*` 的纯函数，不含业务逻辑。

### 数据流（关键，需读多文件才能理解）

1. `data/generate_mock_data.py` 依据 `data/major_catalog.py`（精选专业的科普知识库）
   生成三份 CSV：`schools.csv` / `majors.csv` / `admission_scores.csv`。
2. `gaokao.data_loader` 把 CSV 读成 `gaokao.models` 里的 dataclass，并缓存
   （Streamlit 下用 `st.cache_data`，无 Streamlit 时退化为 `lru_cache`，故可独立测试）。
3. `gaokao.recommender.engine.recommend(student)` 是总编排入口：
   - `recommender/history.py` 把历年录取记录按 (院校,专业) 聚合出 **参考位次/分数/趋势**
     （近年加权）。
   - 对每个候选项依次调用四个算法：`rank_based`（冲/稳/保分档）、`ml_model`（录取概率，
     sklearn 逻辑回归，**无 sklearn 时回退到等价解析式 sigmoid**）、`interest`（RIASEC
     兴趣匹配）、`scoring`（多维综合加权 → 排序分）。
   - 返回 `{冲/稳/保: [Recommendation, ...]}`，每条带人类可读的 `reasons`。
4. 页面消费 `engine` 的结果：导出（`report.py`）、AI 解释（`llm.py`）等都复用同一套
   `Recommendation`，保证界面/文档/AI 口径一致。

### 约定与易错点

- **位次语义**：数字越小越好。比值 `r = 考生位次 / 院校位次`：`r>1` 偏难→冲，`r≈1`→稳，
  `r<1` 有优势→保。阈值常量集中在 `recommender/rank_based.py`，调参改这里。
- **省份/科类**：推荐只对生成器里的省份（见 `generate_mock_data.PROVINCES`）和
  科类（物理/历史）有数据。`data_loader.available_provinces()` 等给出可选项。
- **优雅降级**：`ml_model`（无 sklearn）、`llm`（无 `DEEPSEEK_API_KEY`）、`report` 的
  Word/PDF（无 `python-docx`/`reportlab`）都必须在依赖/密钥缺失时不报错。新增功能请保持这一约定。
- **页面共享状态**：考生信息、兴趣测评、心愿单、推荐结果都存 `st.session_state`，
  统一通过 `gaokao.ui_helpers` 读写（`get_student`/`get_wishlist` 等）。
- **新增页面**：放 `pages/`，文件名形如 `N_emoji_中文.py`，顶部需 `sys.path.insert`
  把 `src/` 加入路径（兼容未 editable 安装的环境），并复用 `ui_helpers` 而非重写逻辑。

### AI 助手（DeepSeek）

`gaokao.llm` 用 `openai` SDK 指向 `https://api.deepseek.com`（默认模型 `deepseek-chat`）。
密钥从 `st.secrets` 或环境变量读 `DEEPSEEK_API_KEY`；真实 `.streamlit/secrets.toml`
已被 `.gitignore` 忽略，仓库内只有 `.streamlit/secrets.toml.example`。

## Conventions

- 默认 **Python**；用户面向文案、数据字段、注释用**中文**，与高考领域一致。
- `.gitignore` 已排除密钥、本地数据库与缓存——不要提交密钥或真实 secrets 文件。
- 模拟数据 CSV 是确定性生成（固定随机种子）的演示数据，可提交。

## Git Workflow

- 默认分支 `main`，当前开发分支 `claude/claude-md-docs-cb60r`。
- 不要主动开 PR，除非用户明确要求。
