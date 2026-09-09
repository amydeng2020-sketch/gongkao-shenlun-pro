# -*- coding: utf-8 -*-
# 细节扣分模块（v0.7）：机构阅卷通用细则的确定性账本
# 原则：内容分（要点/维度/档位）与细节分分离。细节扣分在档位确定后统一扣减，
# 不重复影响任何内容维度。所有参数为机构通用口径的经验校准（粉笔/华图/中公
# 教学共识），非国家公务员局官方硬规则；输出必须标注"机构通用·训练校准"。
# 官方提供细则时用 official_override 仅覆盖当次考试。

DEDUCTION_CATEGORIES = {
    "错别字": "language",
    "标点错误": "language",
    "字数超限": "length",
    "字数不足": "length",
    "标题问题": "format",
    "卷面涂改": "presentation",
}

# 语言类（错别字+标点）合计上限；全局细节扣分上限占满分比例
_LANGUAGE_POOL_CAP = 3.0
_GLOBAL_CAP_RATE = 0.30  # 安全护栏：仅防异常堆叠，正常专项封顶先生效

DEFAULT_DEDUCTION_POLICY = {
    "source": "机构通用口径（粉笔/华图/中公教学共识）·训练校准，非官方硬规则",
    "语言": {
        "错别字": {"unit_count": 3, "unit_deduction": 1.0, "cap": 3.0,
                 "rule_text": "每3个错别字扣1分，重复错字不重复计，最多扣3分"},
        "标点错误": {"unit_count": 5, "unit_deduction": 1.0, "cap": 1.0,
                  "rule_text": "标点错误较多或书写模糊扣1分（明显错误≥5处计），与错别字合计不超过3分"},
    },
    "小题字数": {
        "超上限": {"unit_count": 30, "unit_deduction": 1.0, "cap": 3.0,
                "rule_text": "超过题面上限每30字扣1分，最多扣3分（超出答题区域另有扫描风险，另行提示）"},
        "低于下限": {"unit_count": 50, "unit_deduction": 1.0, "cap": 3.0,
                  "rule_text": "低于题面下限每50字扣1分，最多扣3分"},
    },
    "作文字数": {
        "超上限": {"unit_count": 50, "unit_deduction": 1.0, "cap": 3.0,
                "rule_text": "超过上限每50字扣1分，最多扣3分"},
        "不足": {"unit_count": 50, "unit_deduction": 1.0, "cap": 3.0,
               "rule_text": "每少50字扣1分，最多扣3分；不足700字三类以下、不足600字四类以下（阈值降档另由定档处理）"},
    },
    "标题": {
        "无标题": {"flat_deduction": 2.0,
                "rule_text": "申发论述未写标题，扣2分（机构通用训练口径）"},
        "不完整": {"flat_deduction": 1.0,
                 "rule_text": "标题不完整或明显不当，扣1分"},
    },
    "卷面": {
        "轻微": {"flat_deduction": 1.0, "cap": 1.0,
              "rule_text": "字迹潦草、卷面不洁、标点模糊扣1分"},
        "严重涂改": {"flat_deduction": 2.0, "cap": 2.0,
                  "rule_text": "涂改严重扣2分，连续涂黑/修正带痕迹明显影响阅卷；特别严重的影响语言表达档位"},
    },
}


def ded_policy_for(question_type):
    if question_type == "申发论述":
        return {"over": DEFAULT_DEDUCTION_POLICY["作文字数"]["超上限"],
                "under": DEFAULT_DEDUCTION_POLICY["作文字数"]["不足"]}
    return {"over": DEFAULT_DEDUCTION_POLICY["小题字数"]["超上限"],
            "under": DEFAULT_DEDUCTION_POLICY["小题字数"]["低于下限"]}


def detail_deduction_errors(findings, official_override):
    """结构校验：非法类别、非法计数、非法官方覆盖键。"""
    errors = []
    allowed_cats = set(DEDUCTION_CATEGORIES)
    for idx, f in enumerate(findings or []):
        if not isinstance(f, dict):
            errors.append(f"detail_deductions[{idx}] must be an object")
            continue
        cat = f.get("category")
        if cat not in allowed_cats:
            errors.append(f"detail_deductions[{idx}].category {cat!r} invalid; allowed: {sorted(allowed_cats)}")
        count = f.get("count", 0)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(f"detail_deductions[{idx}].count must be a non-negative integer, got {count!r}")
        if f.get("evidence") is not None and not isinstance(f.get("evidence"), str):
            errors.append(f"detail_deductions[{idx}].evidence must be a string")
    if official_override is not None:
        if not isinstance(official_override, dict):
            errors.append("detail_deduction_policy_override must be an object")
        else:
            for k in official_override:
                if k not in allowed_cats and k != "source":
                    errors.append(f"detail_deduction_policy_override unknown key {k!r}")
    return errors


def compute_detail_deductions(question_type, actual_length, length_min, length_max,
                              findings, score_base, rounder, official_override=None):
    """统一计算细节扣分账本。actual_length 由引擎按 check-word-count 口径预算。

    rounder: 引擎的取整函数（小题/作文整数、维度模式半分）。
    返回扣分报告 dict；调用方负责把 total_deduction 应用到 center/raw/interval。
    """
    findings = list(findings or [])
    auto_findings = []
    length_violation = None
    lp = ded_policy_for(question_type)

    # --- 自动字数审计（确定性）---
    if length_max is not None and actual_length > length_max:
        over = actual_length - length_max
        units = over // lp["over"]["unit_count"]
        if units >= 1:
            ded = min(units * lp["over"]["unit_deduction"], lp["over"]["cap"])
            length_violation = {
                "category": "字数超限", "actual_length": actual_length,
                "limit": length_max, "excess": over, "units": units,
                "deduction": round(ded, 2), "rule": lp["over"]["rule_text"],
            }
            auto_findings.append({"category": "字数超限", "count": over, "auto": True,
                                  "basis": f"实际{actual_length}字，超上限{length_max}字{over}字",
                                  "evidence": "", "deduction": round(ded, 2)})
    elif length_min is not None and actual_length < length_min:
        short = length_min - actual_length
        units = short // lp["under"]["unit_count"]
        if units >= 1:
            ded = min(units * lp["under"]["unit_deduction"], lp["under"]["cap"])
            severe_short = question_type == "申发论述" and actual_length < length_min * 0.7
            length_violation = {
                "category": "字数不足", "actual_length": actual_length,
                "limit": length_min, "shortfall": short, "units": units,
                "deduction": round(ded, 2), "rule": lp["under"]["rule_text"],
                "severe_short_essay": severe_short,
            }
            auto_findings.append({"category": "字数不足", "count": short, "auto": True,
                                  "basis": f"实际{actual_length}字，低于下限{length_min}字{short}字",
                                  "evidence": "", "deduction": round(ded, 2)})

    # --- 人工逐项 ---
    items = []
    typo_ded = 0.0
    punct_ded = 0.0
    format_ded = 0.0
    presentation_ded = 0.0
    presentation_notes = []
    override = official_override if isinstance(official_override, dict) else {}

    def _pol(cat):
        if cat in override:
            return override[cat]
        if cat == "错别字":
            return DEFAULT_DEDUCTION_POLICY["语言"]["错别字"]
        if cat == "标点错误":
            return DEFAULT_DEDUCTION_POLICY["语言"]["标点错误"]
        if cat == "标题问题":
            return DEFAULT_DEDUCTION_POLICY["标题"]
        return None

    for f in findings:
        cat = f.get("category")
        count = int(f.get("count", 0) or 0)
        evidence = f.get("evidence", "") or ""
        sub_type = f.get("sub_type", "")
        auto = bool(f.get("auto"))
        basis = f.get("basis", "")
        if cat in ("字数超限", "字数不足"):
            continue
        if cat == "错别字":
            pol = _pol("错别字")
            units = count // pol["unit_count"]
            raw = units * pol["unit_deduction"]
            ded = min(raw, pol["cap"])
            items.append({"category": cat, "count": count, "units": units,
                          "deduction_raw": round(raw, 2), "deduction": round(ded, 2),
                          "evidence": evidence, "auto": auto, "basis": basis, "rule": pol["rule_text"]})
            typo_ded += ded
        elif cat == "标点错误":
            pol = _pol("标点错误")
            units = count // pol["unit_count"]
            raw = units * pol["unit_deduction"]
            ded = min(raw, pol["cap"])
            items.append({"category": cat, "count": count, "units": units,
                          "deduction_raw": round(raw, 2), "deduction": round(ded, 2),
                          "evidence": evidence, "auto": auto, "basis": basis, "rule": pol["rule_text"]})
            punct_ded += ded
        elif cat == "标题问题":
            pol = _pol("标题问题")
            if sub_type in ("无标题", "missing"):
                raw = float(pol["无标题"]["flat_deduction"]); rule = pol["无标题"]["rule_text"]; st = "无标题"
            else:
                raw = float(pol["不完整"]["flat_deduction"]); rule = pol["不完整"]["rule_text"]; st = "不完整"
            items.append({"category": cat, "sub_type": st, "count": count,
                          "deduction_raw": round(raw, 2), "deduction": round(raw, 2),
                          "evidence": evidence, "auto": auto, "basis": basis, "rule": rule})
            format_ded += raw
        elif cat == "卷面涂改":
            severity = f.get("sub_type", "轻微")
            if severity in ("严重", "severe", "严重涂改"):
                pol = DEFAULT_DEDUCTION_POLICY["卷面"]["严重涂改"]
                raw = float(pol["flat_deduction"]); rule = pol["rule_text"]; st = "严重涂改"
            else:
                pol = DEFAULT_DEDUCTION_POLICY["卷面"]["轻微"]
                raw = float(pol["flat_deduction"]); rule = pol["rule_text"]; st = "轻微"
            items.append({"category": cat, "sub_type": st, "count": count,
                          "deduction_raw": round(raw, 2), "deduction": round(raw, 2),
                          "evidence": evidence, "auto": auto, "basis": basis, "rule": rule})
            presentation_ded = raw
            presentation_notes.append({"category": cat, "sub_type": st, "count": count, "evidence": evidence,
                                       "rule": rule, "deduction": round(raw, 2)})

    language_raw = typo_ded + punct_ded
    language_ded = min(language_raw, _LANGUAGE_POOL_CAP)
    length_ded = length_violation["deduction"] if length_violation else 0.0
    total_raw = language_ded + length_ded + format_ded + presentation_ded
    global_cap = round(score_base * _GLOBAL_CAP_RATE, 2)
    total_ded = max(0.0, min(total_raw, global_cap))
    capped = total_raw > total_ded + 1e-9

    return {
        "items": items,
        "auto_findings": auto_findings,
        "length_violation": length_violation,
        "language_pool": {
            "错别字": round(typo_ded, 2), "标点错误": round(punct_ded, 2),
            "raw_total": round(language_raw, 2), "applied": round(language_ded, 2),
            "cap": _LANGUAGE_POOL_CAP, "capped": language_raw > _LANGUAGE_POOL_CAP + 1e-9,
        },
        "length_deduction": round(length_ded, 2),
        "format_deduction": round(format_ded, 2),
        "presentation_notes": presentation_notes,
        "presentation_deduction": round(presentation_ded, 2),
        "total_deduction": round(total_ded, 2),
        "total_raw": round(total_raw, 2),
        "global_cap": global_cap,
        "global_capped": capped,
        "actual_length": actual_length,
        "policy_source": (override.get("source") if isinstance(override, dict) and override.get("source")
                          else DEFAULT_DEDUCTION_POLICY["source"]),
        "official_override_applied": bool(override),
        "deduction_principle": "内容分与细节分分离：要点覆盖与档位确定后，细节扣分统一扣减；同一问题不在内容维度重复扣分",
    }
