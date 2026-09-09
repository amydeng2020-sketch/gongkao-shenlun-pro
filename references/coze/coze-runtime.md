# Coze 平台运行适配（安装时追加，优先级等同 runtime 契约）

本 Skill 原生为支持 MCP 的 Agent 平台（WorkBuddy/Claude Code 等）设计。
在 Coze 平台中没有 MCP 通道，但评分引擎 `scripts/review_engine.py` 是纯标准库 Python
脚本（零网络、零第三方依赖），通过 bash 以 stdin/stdout JSON 方式调用，效果与 MCP
完全等价。**评分规则、点池构建、档位计算、校验门禁一律不变，仅调用通道改为 CLI。**

## 调用通道映射

| 原 MCP 工具 | Coze CLI 等价调用（在 skill 目录下执行） |
|---|---|
| `shenlun_grade_once` | `echo '<JSON>' \| python3 scripts/review_engine.py grade-once` |
| `shenlun_validate_user_output` | `echo '<JSON>' \| python3 scripts/review_engine.py validate-user-output` |
| `analyze-once` | `echo '<JSON>' \| python3 scripts/review_engine.py analyze-once --output <receipt路径>` |
| `finalize-analysis` | `echo '<JSON>' \| python3 scripts/review_engine.py finalize-analysis` |
| 字数校验 | `python3 scripts/review_engine.py check-word-count ...`（仅契约要求时） |

注意：
- `analyze-once` 成功后 stdout 返回 `{"success":true,"output":"<receipt文件路径>"}`，
  回执 JSON 写到该路径文件；`finalize-analysis` 传该 receipt 路径。
- `grade-once` / `validate-user-output` 直接 stdout 输出完整结果 JSON。
- JSON 载荷请写入临时文件再用 stdin 重定向（避免 shell 转义中文/引号问题）：
  `python3 scripts/review_engine.py grade-once < /tmp/grade_input.json`
- 临时输入文件和回执放在系统临时目录；题干、材料、作答不得复制到其他长期文件。
- `safe_review_runner.py`、`shenlun_mcp_server.py`、`pretooluse_guard.py` 是 MCP
  平台组件，Coze 不使用；**不要**为了走它们而绕过引擎。
- 其余所有铁律（一次评分、失败只统一修正一次、不手算分数、不编造材料依据、
  OCR 不确定标待核对、正文直发）全部原样遵守。

## 输入 JSON 最小字段

- analyze-once：`{"question_text":"题干","material_text":"给定资料"}`，
  有参考答案时加 `"reference_answers":[{"answer_text":"..."}]`
- grade-once：`question_text`、`material_text`、`user_answer`（考生作答），
  可选 `reference_answers`、`full_score`；完整字段以
  `references/contracts/grade-once-runtime.md` 为准。
- validate-user-output：`{"text":"最终正文","validation_context":<grade/analyze回执中的 output_validation_context>}`

## 图片/PDF 输入

Coze 用内置多模态读图能力识别题目截图、答题纸照片；识别结果转成文本后走同一流程。
手写体/图片看不清的内容标记"待核对"，不猜测、不据此判漏点。PDF 用平台 PDF 解析能力提取文本。
