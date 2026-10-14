# 模型主导简历审查：官方依据与适用边界

支持决策：[怎样证明模型主导方案写得更好且没有降低真实性？](https://github.com/Zhangyinglun/monkey-resume/issues/6)。
本研究由独立只读研究会话核验四个官方页面，主线程保存。
研究不证明新流程已经优于旧流程，也没有运行生产模型 API 评估。

## 官方建议

| 官方材料 | 核验所得 | 本项目的应用边界 |
| --- | --- | --- |
| [GPT-6 提示指南](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices) | 指南是系列模型的起点，主要基于 Astra 的观察，需在实际模型和工作负载上评估；建议审计 skills/AGENTS 的影响、明确表达风格并校准测试范围。 | 简化重复和冲突的流程要求；不能据此取消事实、遗漏和实际格式检查。 |
| [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 先定义目标、任务数据和指标，覆盖常见、边界、对抗案例，用人工反馈校准自动评分；模型裁判存在位置和长度偏好。 | 固定资料和 JD 比较新旧流程，分别判断真实性、覆盖和表达，允许平局。 |
| [Graders](https://developers.openai.com/api/docs/guides/graders) | 独立 grader 也需要与人工质量判断对齐，加入边界案例并防止 grader hacking。 | 裁判输出 PASS、链接合法或结构合法都不能当作真实标签；这份文档包含训练语境，不要求简历门禁使用平滑总分。 |
| [Summarization evaluation cookbook](https://developers.openai.com/cookbook/examples/evaluation/how_to_eval_abstractive_summarization) | 区分 relevance、coherence、consistency、fluency；事实一致性要求输出陈述被原文蕴含。 | 可借鉴原文蕴含与重要内容覆盖；配方已归档，旧模型、API 和示例数字不直接采用。 |

关键原文：

> “evaluate them with your chosen model and workload.” — GPT-6 指南

> “Use human feedback to calibrate automated scoring.” — Evaluation best practices

> “A factually consistent summary contains only statements that are entailed by the source document.” — Summarization cookbook

## 本地设计：五个应用原则

1. **冻结对照条件。** 同一资料、JD、澄清答案和输出约束，记录模型、提示、加载的 skills 和设置。预先标注事实边界、重要贡献及可接受取舍；保留没有用于提示调整的验证案例。
2. **分开盲读和查证据。** 先匿名草稿与原始 JD，冻结阅读判断；再提供完整有效证据和更正记录。盲读判断表达与相关性，事实阶段判断蕴含和遗漏。作者的旧 PASS 结论不作为输入；删减理由在独立事实核对后才用于评估取舍。
3. **双向核验。** 从正文检查每个断言是否有依据；从完整证据检查强相关贡献是否被无理由遗漏。逐项核对指标对象、动作、单位、分母、时间、环境、归属和完成状态；数字出现在某处不证明它支持这句话。
4. **测试裁判。** 错误变体包括正确数字被移到其他对象、ownership 升级、重要经历遗漏；负对照包括事实正确的同义改写和合理删减。记录漏报、误报和裁判分歧。成对比较需交换顺序检查位置偏好，不能为等长而删去真实贡献。
5. **错误不能被文笔抵消。** 英文表达的胜平负与事实、重要遗漏、关键表达、格式失败分别报告。实际页面检查与内容绑定同一版本。有限样本最多证明特定样例下未观察到某类问题，不证明普遍零错误。

## 独立上下文的证据边界

官方材料支持独立 grader、明确评分输入以及对偏差的警惕；没有规定
“简历必须 fresh-context 两阶段审查”，也没有证明隔离上下文即可消除偏差。
两阶段是本项目的候选设计，不是 OpenAI 的简历专项规定。

仓库现有 `references/recruiter-review-protocol.md:11` 要求 fresh-context，
但刻意不提供 Ledger/Source Snapshot；这一盲读角色不能单独承担完整事实
及遗漏审查。该协议的引文验证也不能证明语义蕴含。

## 数量和通过标准

核验的四页没有规定通用重复次数、跨模型数量、简历通过阈值或最小字号。
样例数量、重复范围、对照标准及页面可读性条件均属于本地设计。
已有用户要求是严格一页和四类关键返修问题，不是官方评分标准。

主线程另行开展 `docs/design/evaluation/` 中的合成审阅小试。它测试裁判
能否发现已知错误，不等于完整新旧生成流程对照，不证明真实简历质量改善。
