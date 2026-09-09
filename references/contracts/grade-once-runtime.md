# grade-once 普通批改短契约

本文件是普通批改的首选契约。一次构造、一次调用；仅当入口返回本文件无法解决的结构错误，才受控读取完整契约、Schema 或源码一次。不得手工改分或反复调试。

## 执行

1. 一次准备完整对象，文本不写入代码或 shell。
2. WorkBuddy 一次调用 `shenlun_grade_once`，对象直接作参数，由工具序列化。
3. 根据回执生成一次最终正文；评分成功后不得重建点池或再次调用评分入口。
4. 一次调用 `shenlun_validate_user_output`，提交正文和原样上下文；校验失败只修正文并复校。
5. 只发送 `approved_text`。

### 传输与止损

工具不可见时先搜索；仍未加载或宿主不支持 MCP，停止正式评分并提示用户启用/重启申论插件。禁止 `python3 - <<'PY'`、`python -c`、临时代码/JSON、重定向、shell 拼输入或直接调用评分 Runner；插件守卫会拒绝旧路径。

`safe_review_runner.py` 仅由 MCP Server 内部调用，普通智能体不得把它当作终端降级入口。

首次失败只改错误列表所指路径，统一修正后重试一次；不得改其他已通过字段。第二次失败或同错再现即停止。脚本启动、JSON 解析失败和 60 秒超时都计入次数；不得查源码、Schema、`--help`、方法卡或旧命令链。

## 最小输入

```json
{
  "question_text": "完整原题题干",
  "full_score": 15,
  "max_length": 300,
  "material_text": "本题对应完整材料",
  "user_answer": "清理明显OCR错误后的完整作答",
  "points": [],
  "point_pool_review": {
    "status": "verified",
    "evidence": "已完成材料查漏、同功能合并、不同功能拆分和背景/例子边界复核"
  },
  "holistic_review": {
    "evidence": "整体任务完成度与结构依据",
    "overall_quality": 3,
    "order_logic_status": "sound",
    "duplicate_status": "none",
    "structure_required": true,
    "structure_status": "clear"
  }
}
```

`dimensions`/`dimension_levels`、`task_components`、稳定 ID、方法卡、账本和材料范围可省略，由入口编译。若确需人工给维度等级，可把对应题型的 `dimension_levels` 放在顶层或本题审核对象内；两处同时提供时必须完全一致。

### 硬性扣分（可选，v0.7）

需要对错别字、标点、标题、卷面等机构通用细则扣分时，在最小输入上追加 `detail_deductions`（数组）。规则总表见 `references/scoring-core.md`「硬性扣分账本」。

```json
"detail_deductions": [
  {"category": "错别字", "count": 4, "evidence": "考生原句：把'履职'写成'履职'两处、'亟待'写成'急待'两处"},
  {"category": "标点错误", "count": 6, "evidence": "第二段逗号句号混用、引号缺失，见考生原文第2段"},
  {"category": "标题问题", "sub_type": "无标题", "count": 1, "evidence": "作答首行直接为正文，无标题行"},
  {"category": "卷面涂改", "sub_type": "轻微", "count": 1, "evidence": "答题卡首段有两处划线涂改"}
]
```

- `category` 只用：`错别字` / `标点错误` / `标题问题` / `卷面涂改`。**字数超限、字数不足由引擎按 `check-word-count` 口径自动审计，禁止人工提交。**
- `count` 为非负整数；`evidence` 必须是考生作答中可核验的原句或定位说明，找不到原文依据的条目不得提交；OCR 不确定的错别字/标点不计入。
- `sub_type`：标题问题用 `无标题` / `不完整`；卷面涂改用 `轻微` / `严重涂改`。
- 扣分在内容定档后统一扣减（错别字每3个扣1分、上限3分；标点≥5处扣1分；错别字+标点合计封顶3分；无标题扣2分；卷面轻微1分/严重涂改2分；小题超字每30字扣1分、作文每50字扣1分），全部为机构通用口径的训练校准，非官方硬规则。
- 大作文不足700字强制三类上限、不足600字强制四类上限（`forced_by_word_count`），由引擎自动判定。
- 用户提供当次考试官方细则时，可传 `detail_deduction_policy_override`（对象，可含 `source` 及按类别的覆盖参数），仅覆盖当次；非法类别或负计数会被入口闭锁（exit=2）。
- 回执 `result.detail_deductions` 给出逐条明细与 `total_deduction`；**有扣分时正文必须输出「硬性扣分明细」段**（类别、数量、扣分、依据原句，并注明"机构通用口径·训练校准，非官方硬规则"）；无扣分不输出该段。

### 整卷批改模式（v1.5.0）

同一套卷多题一次性判分时（整卷 SOP 见 SKILL.md「整卷批改模式」）：

- **错别字/标点只在全卷最大主体题（大作文35分；无作文则最大应用文）的 payload 提交一次**，`count` 为全卷可确认错字总数，`evidence` 按题号分组：
  ```json
  {"category": "错别字", "count": 18, "evidence": "全卷归集（小题踩点给分不单独扣错别字）：题1原句'……'善亮→善意；题3原句'……'咸受→感受；题5原句'……'实干为互→实干为要……"}
  ```
- 小题 payload **不传** `detail_deductions` 里的错别字/标点项；卷面涂改作为全卷一条随归集题提交（无答题卡图片不评）。字数仍逐题自动审计，不归集。
- **分数引用纪律**：每题最终分只取回执 `result.center_value`（已扣后）；扣前内容分看 `result.detail_deductions_applied.pre_deduction_raw_center`，扣分看 `total_deduction`。禁止手工"扣前−扣分"推算后写进正文或归档（曾出现 21−2 误报 17 的事故）。整卷总分＝各题 center_value 之和，须代码验算。
- 题型/分值以联网获取的真题题干为准；题干未触发路由时报"Question type confirmation required"，可按任务动词判定后在题干末尾追加题型确认标注重交，题干原文与材料禁改。

- 普通小题：提交 `points` 和 `holistic_review`。缺省维度时，入口根据点池覆盖与整体质量生成展示维度；正式分仍由逐点计分决定。
- 应用文：提交 `points` 和 `application_review`。缺省维度时，入口根据身份、明确格式要求、目的、内容、结构和语气状态生成五维；未明确要求的标题、称谓、落款、日期不进入格式扣分。
- 大作文：提交材料使用点和 `essay_review`。缺省维度时，再填写 `language_status`（strong/adequate/weak/poor/unreadable）与 `example_support_status`（strong/adequate/partial/weak/missing）；入口据此和既有立意、材料转化、论证线、分论点体系状态生成六维。

### 应用文与大作文的最小语义对象

两类题不能用小题 `holistic_review` 代替；字段必须来自题干、材料和作答判断，不用占位词。

- `application_review` 必须填写：`identity_status`（accurate/partial/wrong）、`genre_format_status`（complete/partial/missing）、`purpose_audience_status`（strong/adequate/weak）、`content_status`（complete/partial/missing）、`structure_status`（clear/partial/unclear）、`tone_status`（appropriate/partial/wrong）、`template_use_status`（appropriate/overgeneralized/not_applicable）、`evidence`。格式只有在题目明确要求时检查。

- `essay_review` 必须填写：`central_thesis`、`sub_argument_chain`（至少两条）、`relationship_type`、`prompt_relation_required`、`relationship_centrality`（core/supporting/not_applicable）、`relationship_coverage_status`（complete/partial/mentioned_only/missing/distorted/not_applicable）、`thesis_scope_status`（accurate/narrowed/off_topic）、`sub_argument_system_status`（sound/mixed_levels/material_parallel/broken）、`material_transformation_status`（transformed/mixed/mechanical）、`material_support`、`reasoning_bridge`、`counterargument_or_boundary`（字符串或 null）、`return_to_thesis`、`topic_specificity`（strong/adequate/weak）、`argument_line_status`（sound/weak/broken）、`material_support_status`（strong/partial/weak）、`template_risk`（none/local/pervasive）、`judgment_evidence`、`evidence`；省略人工维度时还须 `language_status`、`example_support_status`。

- `essay_review.judgment_evidence` 包含：`prompt_relation_quote`、`relationship_centrality_rationale`、`central_thesis_quote`、`side_a_quote`、`side_b_quote`、`relationship_bridge_quote`、`scope_rationale`、`sub_argument_audit`、`material_transformation_quote`。`sub_argument_audit` 与分论点一一对应；非关系题使用 `not_applicable/null`。

## points 最小项

```json
{
  "point_id": "p1",
  "point_text": "该点的作答功能",
  "material_evidence": ["材料连续短句一", "材料连续短句二"],
  "coverage_status": "完整覆盖",
  "user_quote": "考生作答中的连续短句",
  "point_value": 3,
  "expansion_level": "基本展开",
  "importance": "core"
}
```

- `coverage_status`：只用 `完整覆盖` / `等义表达` / `部分覆盖` / `未覆盖` / `超出材料`。
- 非“未覆盖”必须给 `user_quote`；“未覆盖”可留空。工具会把可验证的标点、空白或省略写法回定位为考生作答中的原句；无法回到作答的引用仍会闭锁。
- `material_evidence` 把连续原文分作数组元素，元素独立且无顺序要求。省略号只用于同一原文省略中段，片段须保持原序；跨段、跨人物或顺序不确定时用数组。所有片段都须在材料中找到。
- `expansion_level` 可省略；省略时由覆盖状态推导。若填写，只用“充分展开 / 基本展开 / 简略提及 / 仅列标题 / 未提及”；常见的“部分展开”会按覆盖状态推导，不需要重试。
- OCR 不清晰时标记 `ocr_status="uncertain"` 和说明，不得因模糊直接判未覆盖/材料外。
- 材料外表述放入 `extra_material_claims`，只作局部准确性记录，不扩充点池、不吞掉已覆盖内容。

## 参考答案

有参考答案时传 `reference_answers=[{answer_text,label}]`、实际份数 `expected_reference_answer_count`，以及 `reference_calibration={status:"verified",complete_review:true,candidates:[...]}`。每个候选包含 `candidate_id`、`answer_index`、参考答案连续原文 `candidate_text`、材料证据、`disposition` 和 `mapped_point_ids`。

`disposition` 只用 `included/merged/excluded`：前两者给证据和映射点，排除项说明理由。参考答案是重要候选，回题干材料核验；无据不纳入。发现冲突时说明“参考答案—材料—AI选择及理由”，不静默改口径。

无参考答案时，省略上述字段。入口会按当前输入生成 `reference_available=false` 和 `reference_discovery=not_found`。

## 语法归一化边界

入口可自动处理标点/引号/空白差异、已知字段别名、参考答案发现元数据和可回到材料的证据片段包装。回执中的 `input_normalization` 只记录字段名、动作和数量，不包含题干、材料、作答或参考答案原文。

不允许自动改变题干、材料、作答、点池、点值、覆盖状态、任务组件、参考答案正文/份数/校准结论。未知状态词、证据找不到、参考数量冲突或任务边界冲突必须闭锁。

## 成稿

直接使用 `grade-once` 返回的：

- 档位、档内位置、中心值、区间、置信度。
- `sentence_audit` 或 `paragraph_audit`。
- `selected_method_guides` 中的中文方法名、步骤和边界。
- `output_validation_context`。

小题/应用文输出顺序：题干责任→方法使用→逐句/逐条证据评点→主要失分与修复→档位和建议分。大作文按题干拆解→方法→自然段点评→整体修改→档位和建议分。

所有模式题型均须完整输出，不得摘要。应用文档位按回执原样转译，不改为“一/二/三档”。

不显示内部 ID、伪单点分、命令、路由、门禁或文件路径。有参考答案时不重复完整答案；无参考答案时默认给示范答案。
