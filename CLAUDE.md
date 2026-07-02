# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gaokao-zhiyuan-recommender` — 基于多维数据分析与推荐算法的高考志愿填报辅助系统，支持分数线预测与个性化志愿推荐.

A Gaokao (China's college entrance exam) application-form (志愿) assistant built as a
**Streamlit** multi-page app. It helps a student get admitted to schools/majors they
like or are suited for, and makes the process fun and understandable. The product is
**white-label-able**（贴牌，见 `branding.py`）并可打包成 Windows 安装包（见 `packaging/`）。

许可证为 **AGPL-3.0**（见 `LICENSE`）。

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

Python ≥ 3.10。包通过 `pyproject.toml` 的 src layout 暴露为 `gaokao`，并通过
`pythonpath = ["src"]` 让 pytest 直接 import。`requirements.txt` 是 Streamlit
Community Cloud 的运行时依赖（与 `[project].dependencies` 保持一致，外加可选导出依赖）；
云端不做 editable 安装，页面靠 `sys.path.insert` 找到 `src/`。

## Architecture

三层结构：**核心算法库**（`src/gaokao/`）+ **Streamlit 多页面前端**（`pages/`）+
**数据**（`data/`）。算法与 UI 解耦——所有页面只调用 `gaokao.*` 的纯函数，不含业务逻辑。

### 核心模块（`src/gaokao/`）

- `models.py` — 领域 dataclass：`Student` / `School` / `Major` / `AdmissionRecord` /
  `Recommendation`，以及霍兰德 `RIASEC_DIMENSIONS` 和档位常量 `TIERS`（冲/稳/保）。
- `data_loader.py` — CSV → dataclass 加载与缓存；数据来源解析 `resolve_data_dir()`。
- `data_import.py` / `data_schema.py` — 真实数据导入（编码鲁棒、列别名映射、脏行清洗）
  与表结构校验。
- `rank_score.py` — 分数⇄位次换算（一分一段表），按 (省份, 科类) 参数化，对数位次空间插值。
- `electives.py` — 选科要求解析与匹配（`satisfies()` 判定考生选科能否报考某专业）。
- `assessment.py` — 兴趣测评题库与计分（情景二选一，产出 RIASEC 向量）。
- `major_knowledge.py` — 专业科普内容辅助。
- `branding.py` — 贴牌配置（读根目录 `branding.json`，缺失用默认值）。
- `llm.py` — DeepSeek AI 助手（见下）。
- `report.py` — 志愿表导出（Markdown / Word / PDF，优雅降级）。
- `ui_helpers.py` — 页面共享状态读写（`get_student` / `get_wishlist` 等）。
- `recommender/` — 推荐算法子包（见下）。

### 推荐子包（`src/gaokao/recommender/`）

- `engine.py` — **总编排入口** `recommend(student)`。
- `history.py` — 把历年录取记录按 (院校,专业) 聚合成 `HistoryStat`：参考位次/分数、
  趋势 `trend`、波动 `rank_cv`（大小年）、`plan_ratio`（扩招/缩招）等（近年加权）。
- `rank_based.py` — 冲/稳/保分档（位次比阈值）。
- `ml_model.py` — 录取概率**区间**预测（`predict_intervals` / `predict_interval`），
  基于历年位次波动的正态校准 + 招生计划变化修正；`confidence_label` 给把握度。
  无 sklearn 时回退到等价解析式 sigmoid。
- `interest.py` — RIASEC 兴趣匹配。
- `scoring.py` — 多维综合加权 → 排序分。
- `compare.py` — 院校对比 `compare()`：对任意若干 (院校,专业) 算齐可比指标，
  **不做冲稳保过滤**，复用同一套子算法保证口径一致。
- `trending.py` — 热门专业榜 `rank_hot_majors()`（热度 + 就业率 + 开设广度）。

### 数据流（关键，需读多文件才能理解）

1. `data/generate_mock_data.py` 依据 `data/major_catalog.py`（精选专业的科普知识库）
   生成三份 CSV：`schools.csv` / `majors.csv` / `admission_scores.csv`。
2. `gaokao.data_loader` 把 CSV 读成 `gaokao.models` 里的 dataclass，并缓存
   （Streamlit 下用 `st.cache_data`，无 Streamlit 时退化为 `lru_cache`，故可独立测试）。
   **数据来源** `resolve_data_dir()`：环境变量 `GAOKAO_DATA_DIR` > `data/real/`（导入的
   真实数据，被 gitignore）> `data/`（模拟，兜底）。真实数据经 `gaokao.data_import`
   （编码鲁棒、列别名映射、脏行清洗、`gaokao.data_schema` 校验后落盘）或 **⚙️ 数据源** 页
   导入；标准表结构见 `data/REAL_DATA.md`。
3. `gaokao.recommender.engine.recommend(student)` 是总编排入口：
   - `history.aggregate(...)` 聚合出 `HistoryStat`（参考位次/分数/趋势/波动/计划变化）。
   - 第一遍：`electives.satisfies(major.subject_req, student.electives)` 过滤选科不符的，
     再用 `rank_based.classify` 分到冲/稳/保区间内。
   - 批量 `ml_model.predict_intervals(...)` 算录取概率区间（含招生计划变化修正），
     `confidence_label` 给把握度；`interest.match` 算兴趣匹配；`scoring.composite` 算综合分。
   - 返回 `{冲/稳/保: [Recommendation, ...]}`，每条带人类可读的 `reasons`（含大小年、扩招/
     缩招、兴趣契合、层次偏好等提示）。
4. 页面消费 `engine` / `compare` / `trending` 的结果：导出（`report.py`）、AI 解释（`llm.py`）
   都复用同一套 `Recommendation`，保证界面/文档/AI 口径一致。

### 页面（`pages/`，文件名 `N_emoji_中文.py`）

信息录入 / 兴趣测评 / 志愿推荐 / 卡片选校 / 专业百科 / 数据大屏 / AI助手 / 我的志愿表 /
院校对比 / 一分一段 / 数据源 / 院校查询。志愿推荐支持三种方式：综合 / 按兴趣 / 热门。

### 约定与易错点

- **位次语义**：数字越小越好。比值 `r = 考生位次 / 院校位次`：`r>1` 偏难→冲，`r≈1`→稳，
  `r<1` 有优势→保。阈值常量集中在 `recommender/rank_based.py`，调参改这里。
- **省份/科类**：模拟数据覆盖 `generate_mock_data.PROVINCES`（北京/广东/江苏/四川/湖南/
  河南）和科类物理/历史。一分一段换算器（`rank_score.py`）还支持 `data/segments/` 的真实
  种子，含 **3+3 综合**（北京/天津/山东/浙江/上海/海南，按各省满分自动适配）；
  `data_loader.available_provinces()` / `available_subjects()` / `rank_score.segment_pairs()`
  给出可选项。
- **优雅降级**：`ml_model`（无 sklearn）、`llm`（无 `DEEPSEEK_API_KEY`）、`report` 的
  Word/PDF（无 `python-docx`/`reportlab`）、`branding`（无 `branding.json`）都必须在依赖/
  密钥/配置缺失时不报错。新增功能请保持这一约定。
- **页面共享状态**：考生信息、兴趣测评、心愿单、推荐结果都存 `st.session_state`，
  统一通过 `gaokao.ui_helpers` 读写（`get_student`/`get_wishlist` 等）。
- **新增页面**：放 `pages/`，文件名形如 `N_emoji_中文.py`，顶部需 `sys.path.insert`
  把 `src/` 加入路径（兼容未 editable 安装的环境），并复用 `ui_helpers` 而非重写逻辑。
- **贴牌**：改根目录 `branding.json`（产品名/副标题/机构名/免责声明）即可，无需改代码。

### AI 助手（DeepSeek）

`gaokao.llm` 用 `openai` SDK 指向 `https://api.deepseek.com`（默认模型 `deepseek-chat`）。
密钥从 `st.secrets` 或环境变量读 `DEEPSEEK_API_KEY`；真实 `.streamlit/secrets.toml`
已被 `.gitignore` 忽略，仓库内只有 `.streamlit/secrets.toml.example`。

## 数据目录（`data/`）

- `schools.csv` / `majors.csv` / `admission_scores.csv` — 确定性生成的模拟数据（可提交）。
- `real/` — 导入的真实逐校录取数据（gitignore，启动时优先使用）。
- `segments/` — **真实公开**的一分一段种子（各省考试院公布的成绩分段统计，属公开事实，
  可提交）；`sources.json` 登记出处。文件名 `{省份}_{科类}_{年份}.csv`，列 `score,rank`。
- `major_catalog.py` — 精选专业科普知识库（生成器的依据）。
- `import_admissions_xlsx.py` / `import_segments_xlsx.py` — 把购买的 Excel 转成标准
  三表 / 一分一段种子的脚本。
- 详细接入指南见 `data/REAL_DATA.md`。

## Conventions

- 默认 **Python**；用户面向文案、数据字段、注释用**中文**，与高考领域一致。
- `.gitignore` 已排除密钥、本地数据库与缓存——不要提交密钥或真实 secrets 文件。
- 模拟数据 CSV 是确定性生成（固定随机种子）的演示数据，可提交；一分一段种子是真实公开数据，
  也可提交。逐校真实录取数据（`data/real/`）不可提交。

## Git Workflow

- 默认分支 `main`，当前开发分支 `claude/claude-md-docs-u362wg`。
- 不要主动开 PR，除非用户明确要求。
