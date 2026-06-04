# 真实数据接入指南

系统默认使用 `data/` 下**确定性生成的模拟数据**做演示。要接入真实录取数据，把数据
归一化成下面三张标准表，导入到 `data/real/`（已被 `.gitignore` 忽略，不会入库）。
启动时系统会**自动优先使用** `data/real/`，缺失时回退到模拟数据。

> ⚠️ 模拟数据仅供演示，**不代表真实录取结果**。正式填报请以各省考试院与院校招生章程为准。

## 数据来源优先级

1. 环境变量 `GAOKAO_DATA_DIR`（指向含三张表的目录）
2. `data/real/`（导入的真实数据）
3. `data/`（内置模拟数据，兜底）

## 标准表结构

三份 CSV，编码 UTF-8 或 GBK 均可；列名可用常见中文（导入器自动识别别名）。

### schools.csv（院校）
| 列 | 必需 | 说明 |
|---|---|---|
| id | ✅ | 院校唯一标识 |
| name | ✅ | 院校名称 |
| province | ✅ | 院校所在省份 |
| city | ✅ | 城市 |
| level | ✅ | 层次：985/211/双一流/普通 |
| type | ✅ | 类型：综合/理工/师范… |
| tags | | 标签，用 `|` 分隔 |

### majors.csv（专业）
| 列 | 必需 | 说明 |
|---|---|---|
| id | ✅ | 专业唯一标识 |
| name | ✅ | 专业名称 |
| category | ✅ | 学科门类：工学/理学/医学… |
| school_id | ✅ | 所属院校 id（须存在于 schools） |
| riasec_code | | 霍兰德主导兴趣码，如 `IR`；缺失按门类兜底 |
| heat | | 热度 0~100；缺省 50 |
| employment_rate | | 就业率 0~1；缺省 0.85 |
| intro / core_courses / career_paths / industry_outlook / suits | | 科普字段，缺省为空 |

### admission_scores.csv（历年录取）
| 列 | 必需 | 说明 |
|---|---|---|
| school_id | ✅ | 须存在于 schools |
| major_id | ✅ | 须存在于 majors |
| year | ✅ | 录取年份 |
| province | ✅ | **生源省份**（高考按省划线，务必准确） |
| subject_type | ✅ | 科类：物理 / 历史 |
| min_score | ✅ | 最低录取分 0~750 |
| min_rank | ✅ | 最低录取位次（正整数） |
| plan_count | ✅ | 招生计划数 |

## 导入方式

### 命令行
```bash
python -m gaokao.data_import 院校.csv 专业.csv 录取.csv --out data/real
```
校验通过才会写入；失败会列出问题且不改动现有数据。

### 应用内
打开 **⚙️ 数据源** 页，上传三份 CSV，一键校验并导入。

## 校验规则

- 三表齐全、必需列齐全；
- `admission_scores` 引用的 school_id/major_id 必须存在；
- `subject_type` 仅限 物理/历史；分数 0~750、位次为正；
- 不满足的脏行在导入时被清洗并计数，结构性错误则整体拒绝写入。
