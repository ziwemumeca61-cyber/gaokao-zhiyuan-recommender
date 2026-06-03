# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gaokao-zhiyuan-recommender` — 基于多维数据分析与推荐算法的高考志愿填报辅助系统，支持分数线预测与个性化志愿推荐.

A Gaokao (China's college entrance exam) application-form (志愿) assistant. The intended scope per the README:

- **分数线预测 (Score-line prediction)** — predict admission cut-off scores for schools/majors from historical data.
- **个性化志愿推荐 (Personalized recommendation)** — recommend schools/majors for a student given their score, rank, region, and preferences, using recommendation algorithms over multi-dimensional data.

## Current State

The repository is at its initial commit and contains **no source code yet** — only `README.md`, `LICENSE` (MIT), and a `.gitignore`. There is no build system, dependency manifest, test suite, or application entry point in place.

When scaffolding the project, prefer establishing these first so future work has a foundation: a dependency manifest (`pyproject.toml` or `requirements.txt`), an entry point, and a `tests/` directory. There are no project-specific commands to document until that tooling exists.

## Tech Stack Signals

No code dictates the stack yet, but `.gitignore` is the standard Python template and explicitly anticipates several Python tools — treat this as a **Python project** unless the user says otherwise. The ignore rules call out, among others:

- Web frameworks: **Django** (`db.sqlite3`, `local_settings.py`) and **Flask** (`instance/`)
- Data/ML & apps: **Jupyter** notebooks, **Streamlit** (`.streamlit/secrets.toml`), **Marimo**
- Tooling: **pytest** (`.pytest_cache/`), **ruff**, **mypy**, **uv**/**pip**/**pipenv**/**poetry**/**pdm** lockfiles

These are hints from a generic template, not commitments. Confirm the actual framework/runtime choice with the user before building substantial structure around any one of them.

## Conventions

- Default to **Python** for new code unless directed otherwise.
- The project domain is Chinese (Gaokao). User-facing strings, data fields, and documentation may be in Chinese; keep that consistent with the README's bilingual framing.
- The `.gitignore` already excludes secrets (`.env`, `.streamlit/secrets.toml`), local databases, and caches — respect these and do not commit data files or credentials.

## Git Workflow

- Default branch is `main`. Active development branch for this work is `claude/claude-md-docs-cb60r`.
- Do not open a pull request unless explicitly asked.
