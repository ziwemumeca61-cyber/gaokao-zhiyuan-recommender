"""真实数据导入与 schema 校验测试。"""

import csv
from pathlib import Path

from gaokao import data_import, data_loader
from gaokao.data_schema import read_rows, validate_dataset

MOCK = Path(data_loader.DATA_DIR)


def _write(path, fields, rows, encoding="utf-8-sig"):
    with open(path, "w", newline="", encoding=encoding) as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ---------- schema 校验 ----------
def test_validate_mock_dataset_ok():
    res = validate_dataset(MOCK)
    assert res.ok, res.errors
    assert res.stats["schools.csv"] == 100


def test_validate_reports_missing_file(tmp_path):
    res = validate_dataset(tmp_path)
    assert not res.ok
    assert any("缺少文件" in e for e in res.errors)


def test_validate_catches_bad_reference_and_subject(tmp_path):
    _write(tmp_path / "schools.csv",
           ["id", "name", "province", "city", "level", "type"],
           [{"id": "S1", "name": "甲大学", "province": "四川", "city": "成都",
             "level": "985", "type": "综合"}])
    _write(tmp_path / "majors.csv", ["id", "name", "category", "school_id"],
           [{"id": "M1", "name": "计算机", "category": "工学", "school_id": "S1"}])
    _write(tmp_path / "admission_scores.csv",
           ["school_id", "major_id", "year", "province", "subject_type",
            "min_score", "min_rank", "plan_count"],
           [{"school_id": "S9", "major_id": "M1", "year": "2024", "province": "四川",
             "subject_type": "化学", "min_score": "600", "min_rank": "1000",
             "plan_count": "5"}])
    res = validate_dataset(tmp_path)
    assert not res.ok
    assert any("不存在" in e for e in res.errors)
    assert any("科类" in e for e in res.errors)


# ---------- 编码鲁棒 ----------
def test_read_rows_handles_gbk(tmp_path):
    p = tmp_path / "gbk.csv"
    _write(p, ["id", "name"], [{"id": "S1", "name": "四川大学"}], encoding="gbk")
    rows = read_rows(p)
    assert rows[0]["name"] == "四川大学"


# ---------- 导入往返 ----------
def test_import_roundtrip_from_mock(tmp_path):
    out = tmp_path / "real"
    rep = data_import.import_dataset(
        MOCK / "schools.csv", MOCK / "majors.csv", MOCK / "admission_scores.csv",
        out_dir=out)
    assert rep.ok, rep.validation.errors if rep.validation else "no validation"
    assert validate_dataset(out).ok
    assert rep.written["schools.csv"] == 100


def test_import_remaps_aliases_and_fills_defaults(tmp_path):
    # 外部列名用中文别名，且专业缺兴趣码/热度/就业率
    _write(tmp_path / "s.csv", ["id", "院校名称", "省份", "城市", "层次", "类型"],
           [{"id": "S1", "院校名称": "甲大学", "省份": "四川", "城市": "成都",
             "层次": "985", "类型": "综合"}])
    _write(tmp_path / "m.csv", ["id", "专业名称", "门类", "school_id"],
           [{"id": "M1", "专业名称": "临床医学", "门类": "医学", "school_id": "S1"}])
    _write(tmp_path / "a.csv",
           ["school_id", "major_id", "录取年份", "省份", "科类", "最低分", "位次", "计划数"],
           [{"school_id": "S1", "major_id": "M1", "录取年份": "2024", "省份": "四川",
             "科类": "物理", "最低分": "640", "位次": "800", "计划数": "10"}])
    out = tmp_path / "real"
    rep = data_import.import_dataset(tmp_path / "s.csv", tmp_path / "m.csv",
                                    tmp_path / "a.csv", out_dir=out)
    assert rep.ok, rep.validation.errors if rep.validation else None
    majors = read_rows(out / "majors.csv")
    assert majors[0]["name"] == "临床医学"
    assert majors[0]["riasec_code"] == "IS"      # 医学 -> 默认兴趣码
    assert float(majors[0]["employment_rate"]) == 0.85  # 默认就业率


def test_import_drops_dirty_admission_rows(tmp_path):
    _write(tmp_path / "s.csv", ["id", "name", "province", "city", "level", "type"],
           [{"id": "S1", "name": "甲大学", "province": "四川", "city": "成都",
             "level": "985", "type": "综合"}])
    _write(tmp_path / "m.csv", ["id", "name", "category", "school_id"],
           [{"id": "M1", "name": "计算机", "category": "工学", "school_id": "S1"}])
    _write(tmp_path / "a.csv",
           ["school_id", "major_id", "year", "province", "subject_type",
            "min_score", "min_rank", "plan_count"],
           [
            {"school_id": "S1", "major_id": "M1", "year": "2024", "province": "四川",
             "subject_type": "物理", "min_score": "600", "min_rank": "1000",
             "plan_count": "5"},                                   # 合法
            {"school_id": "S1", "major_id": "M1", "year": "2024", "province": "四川",
             "subject_type": "物理", "min_score": "x", "min_rank": "0",
             "plan_count": "5"},                                   # 非法数值 -> 丢
            {"school_id": "S9", "major_id": "M1", "year": "2024", "province": "四川",
             "subject_type": "物理", "min_score": "600", "min_rank": "1000",
             "plan_count": "5"},                                   # 悬空引用 -> 丢
           ])
    out = tmp_path / "real"
    rep = data_import.import_dataset(tmp_path / "s.csv", tmp_path / "m.csv",
                                    tmp_path / "a.csv", out_dir=out)
    assert rep.ok
    assert rep.written["admission_scores.csv"] == 1
    assert rep.dropped["admission_scores.csv"] == 2


# ---------- 来源解析 ----------
def test_resolve_prefers_env_over_mock(tmp_path, monkeypatch):
    out = tmp_path / "real"
    data_import.import_dataset(
        MOCK / "schools.csv", MOCK / "majors.csv", MOCK / "admission_scores.csv",
        out_dir=out)
    monkeypatch.setenv("GAOKAO_DATA_DIR", str(out))
    assert data_loader.resolve_data_dir() == out
    path, is_real = data_loader.active_source()
    assert is_real and path == out


def test_default_is_mock_when_no_real(tmp_path, monkeypatch):
    monkeypatch.delenv("GAOKAO_DATA_DIR", raising=False)
    # 把真实数据目录指向一个不存在的位置，模拟"未导入真实数据"
    monkeypatch.setattr(data_loader, "REAL_DIR", tmp_path / "no_real")
    assert data_loader.resolve_data_dir() == data_loader.DATA_DIR
    _, is_real = data_loader.active_source()
    assert is_real is False
