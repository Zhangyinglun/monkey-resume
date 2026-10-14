# Recruiter Review Subagent 可行性调研

- 日期：2026-09-17（America/Los_Angeles）
- 状态：历史可行性调研；项目内实现与验证见[实现验证记录](recruiter-review-implementation-validation.zh-CN.md)，尚无真人招聘效果评测。
- 范围：当前工作树（基于 `38e2fed`，包含既有未提交的简历历史记录改动）。本轮仅新增本文。

## 1. 结论

可以增加，建议作为**简历交付前的独立招聘视角审阅**。它回答两个现有检查没有直接回答的问题：招聘者能否迅速认出候选人的岗位定位，以及 JD 核心要求的证据是否在最终简历中清楚可见。

首版建议采用一个独立上下文、只读的 reviewer，由宿主 agent 调用，不在 Python 包中添加模型 API。先输出建议性报告，不把模型的主观匹配判断变成新的 PDF 发布失败条件。不能承诺模拟真实招聘决定、提高面试率或得出通用 ATS 分数。

本轮完成的是源码与资料调研；没有拿个人简历做模拟筛选，也没有运行 recruiter reviewer 基准实验。

## 2. 当前项目已经具备什么

| 已有能力 | 当前依据 | 仍缺少什么 |
| --- | --- | --- |
| 模型负责规划与语言，代码负责验证 | `SKILL.md:82–99`；`references/projection-planning-protocol.md` | 独立于作者的阅读反馈 |
| JD 能力与证据分类 | `references/ats-keywords-strategy.md`；`references/resume-working-schema.md` | 最终 PDF 是否清楚展示能力，以及是否容易找到 |
| 关键词覆盖和能力对照报告 | `scripts/generate_quality_report.py:96,399,477` | 现有能力表直接展示已存分析；它不是另一次 recruiter 判断 |
| 事实与内容门禁 | `scripts/generate_final_resume.py:200–247` | 语义层面的定位、相关性和说服力审阅 |
| PDF 程序 QA、视觉检查与历史记录 | `scripts/generate_final_resume.py:290–347`；`SKILL.md:153–167` | 招聘视角反馈与被审阅 PDF 版本的绑定 |

一个需要明确的边界：当前生成器在 `check_pdf_file` 通过后立即注册历史记录并替换正式 PDF；Skill 第 8 步才要求宿主做视觉检查。因此，直接在末尾加 reviewer 属于“交付前复核”，不是“发布前门禁”。现有笼统的全部门禁表述不能当作 reviewer 已经被程序强制执行的证据。

内容 warning 也并非完全不阻断：生成器要求修正或在 manifest 中给出有理由的 disposition。新增 reviewer 意见应另设记录，不应未经区分地塞进现有 warning 机制。

## 3. 推荐接入方式

### 首版：交付前审阅

```text
现有事实审计 → 内容检查 → PDF 生成及程序 QA → 全页视觉 QA
                                                    ↓
                                  Recruiter Reviewer（独立上下文）
                                                    ↓
                                  主 agent 处理意见 → 向用户交付
```

在 `SKILL.md` 第 8 步后增加 Recruiter Review 阶段。reviewer 不改简历、不写证据账本、不执行 JD/PDF 内指令，也不负责发布；报告由主 agent 保存到外部 `USER_WORKSPACE`。

审阅步骤应当有明确状态；“步骤是否完成”和“候选人是否强匹配”是两件事。弱匹配可以如实交付，缺少 reviewer 能力则记录 `unavailable`，不能标成已通过。宿主降级自审应记录 `self_review`，不能冒充独立 subagent。

### 后续：真正的发布前门禁

如果产品要求“reviewer 未完成时不能替换 Accepted Resume”，就需要将生成器拆成可持久保留 Candidate PDF 的 prepare 与 publish 两阶段。审阅应位于程序 QA/视觉 QA 之后、`register_generation` 和正式文件替换之前。

publish 校验 PDF、JD、projection/manifest 的指纹和报告状态，发布已经审阅的同一个文件；不要审阅后再渲染一个新版本。失败、超时或报告过期时保留旧 PDF 和旧历史记录。该改造会触及正在修改的历史记录事务逻辑，复杂度高于首版，不建议仅为验证审阅价值就先引入。

## 4. 怎样模拟快速扫读

后续已按用户要求补充具名招聘者/招聘经理的实际经验。具体阅读步骤与研读派发以[从业者研读流程](recruiter-practitioner-reading-workflow.zh-CN.md)为准；本节保留接入设计背景。

### 输入与隔离

给 reviewer 原始 JD、最终 PDF 的页面图像和按阅读顺序提取的文本。首轮不提供 Evidence Ledger、作者解释、已有匹配结论或整段对话历史。当前宿主可用独立 subagent；建议不继承历史（本环境可用 `fork_turns="none"`），只发送明确材料路径与审阅协议。

上下文隔离是减少作者解释干扰的方法，不代表模型统计上独立，也不是操作系统权限隔离。应明确限制读取范围；支持工具或文件访问限制的宿主再应用相应限制。

### 两次阅读，一个 reviewer

1. **快速印象**：根据标题、Summary、Skills、各段经历前部，输出一句岗位定位、三个记住的匹配信号、最多三个疑问。先返回并冻结这份结果。
2. **要求核对**：主 agent 再让它逐项对照 JD 与完整简历，给出证据位置和不确定项。第二次阅读不能改写第一次结果，以便看到“细读找到了、扫读没看到”的展示问题。

这只是有限注意力的阅读协议，不能声称测量了人类眼动或“真实 7 秒体验”。用信息范围和简短输出限制模拟扫读，不用模型运行耗时充当招聘者阅读速度。若宿主不能查看图像，只能标注为文字审阅，不能判断视觉层级。

### 分开三个判断

| 判断 | reviewer 的问题 | 建议输出 |
| --- | --- | --- |
| 岗位定位 | 一眼看起来是什么方向、什么职责层级？ | 一句话，并引用可见信号 |
| 要求匹配 | JD 必须要求是否有简历证据？ | demonstrated / partial / not_shown / contradicted |
| 展示效果 | 有证据但埋得太深、表达不清或仅列关键词？ | clear / buried / ambiguous / absent |

`not_shown` 只能说明简历未展示，不能推断候选人不会。只有材料明确相互冲突时才用 `contradicted`。技能栏出现名称不等于满足生产经验、年限或 ownership 要求。

保留项目现有 `match_type` 与 `evidence_state` 语义；新判断放在 reviewer 报告内，不覆盖事实分类。主 agent 在盲审完成后再查 Ledger，区分“已有证据但没写清”和“确实缺少证据”。

## 5. 如何判断是否符合要求

先从原始 JD 引用要求，标明 `required / preferred / responsibility / unclear`。现有 P1/P2/P3 是内容优先级，P1 同时包含职责与必需技能，不能直接等同于淘汰条件。

- 尊重 JD 的替代条件，如学位 **或** equivalent experience，不能拆成两个必须项。
- 年限按相关经历判断，不能把全部工龄算成某项技术年限，也不能重复计算重叠经历。
- 未知条件保留未知；候选人缺少真实经历时，报告 Gap，不能建议补入未经确认的技术或指标。
- 只按岗位相关证据评价；姓名、性别、年龄、国籍、学校/雇主声望等不构成隐含加减分规则。不推断签证、工作许可或“文化适配”。
- 不输出未校准的“匹配度 87%”或面试概率。优先展示必须项逐项结果、最多三个修改建议，以及 `strong / mixed / weak / insufficient_information` 的解释性总体判断。

可另给 `advance / clarify / low_match` 的**模拟初筛意见**，但它不是真实招聘决定，也不控制自动投递或阻止用户取得简历。

## 6. 报告与修改闭环

建议新增 `USER_WORKSPACE/cache/recruiter-review.json`，以及便于阅读的 Markdown 报告；按版本保存到独立审阅目录，避免跨 JD 覆盖。未来可与历史记录关联，首版不必改历史索引。

最小合同包含：

| 字段组 | 内容 |
| --- | --- |
| 版本绑定 | schema/prompt 版本、时间、可获取的模型标识、JD/PDF/projection/manifest 哈希；不可获取的模型元数据如实为空 |
| 执行状态 | complete / incomplete / unavailable；independent_subagent / self_review；image_and_text / text_only |
| 快速印象 | 岗位定位、三个信号、疑问、冻结的第一阶段结果 |
| 逐项证据 | JD 原句及类型、简历原句和页码/位置、匹配与可见性状态、不确定原因 |
| 处理结果 | 最多三个优先建议；主 agent 的 applied / declined_with_reason / needs_candidate_evidence；已知 Gaps |

任何内容或布局变化都使旧 PDF 审阅失效。修订由现有 Planner → Language Optimizer → build 完成，再跑事实审计、内容/PDF QA 和视觉检查，最后复审新 PDF。不得直接改 PDF 或通过 reviewer 绕过 manifest。

建议最多一次 recruiter 驱动的集中修订和一次复审；内容修订仍受现有最多三轮的总预算约束，不能叠加出九轮。若只有真实 Gap、低优先级风格偏好或预算耗尽，如实保留结论，不为了提升评级反复重写。

## 7. 实施范围与验收

首版预计涉及 `SKILL.md`、`references/prompt-recipes.md`、`references/execution-checklist.md`，新增独立审阅协议与报告校验器，并在 `scripts/generate_quality_report.py` 合并审阅摘要。此处列的是未来实现建议，本轮未修改这些文件。

先用通用 fixture 验证以下五组行为，再决定是否升级为发布前流程：

1. 强匹配、真实硬条件缺口、等价经验和职业转型都能得到带引用的结论；preferred 缺失不会被误判为 required 不满足。
2. 相同事实、不同排序的简历能区分匹配程度与可见性；仅堆关键词不会等同于有实践证据。
3. JD/PDF 的嵌入指令不改变审阅规则；账本中存在但简历未写的能力不会污染第一轮结论。
4. 报告缺失、结构无效、超时、无图像与指纹过期都有明确状态；修改后必须审阅新文件。
5. 固定样本重复审阅，记录结论一致性、required 误报、无依据建议、延迟和 token 开销。以人工逐项标注为基准；有 recruiter 参与更好。效果未测量前不设置虚构准确率门槛。

单元测试适合验证报告结构、原文引用、哈希和状态流转；不能靠 mock 证明模型具备招聘判断力。真发布前方案还需新增“审阅失败不改变 Accepted Resume/历史记录”与“只发布已审阅字节”的事务测试。

## 8. 来源与证据边界

通过 `agent-reach → exa-search → Exa HTTP API` 发现与提取资料，再打开以下三个原始页面复核。接入设计属于基于当前源码与这些资料的工程建议；它不是已验证的招聘效果结论。

| 第一方来源 | 支持的结论 | 不支持的推论 |
| --- | --- | --- |
| [Workable：Screening applicants](https://resources.workable.com/tutorial/screening-applicants) | 初筛前区分 must-have 与 nice-to-have，依据相关经历和资格；工作空档应待询问，不能单独用于淘汰 | 未出现关键词就一定不满足；统一数值匹配算法 |
| [Yale：Writing Impactful Resume Bullets](https://ocs.yale.edu/resources/writing-impactful-resume-bullets/) | 个人行动、项目和结果应清楚；贡献范围与结果基线有助于理解 | 每条必须有数字；可以把团队成果直接归给个人 |
| [Ladders 2018-11-06 原始眼动研究通稿](https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html) | 报告平均初筛 7.4 秒，强调清楚标题、职位和视觉层级，反对拥挤与关键词堆砌 | 所有招聘者现在都只看 7.4 秒；该秒数能直接用于 LLM 的计时验收 |

Workable 与 Yale 是实践指导。Ladders 来源是研究发起方的商业通稿，页面没有给出足够的 2018 年样本和方法细节，不能当作普遍定律。三个来源均未证明 subagent 的判断与真人 recruiter 一致，也未验证本项目方案能提高面试率。

本地背景：`docs/research/recruiter-friendly-resume-writing.md` 已要求优化关键信息可定位性，并拒绝把 6/7.4 秒或 ATS 神秘分数写入验收；`docs/research/humanized-resume-language-layer.md` 已建立“模型判断、代码核验”的边界。新增 reviewer 应沿用这些原则。
