# 招聘从业者的简历筛选实践与 Subagent 研读流程

- 调研日期：2026-09-17（America/Los_Angeles）
- 状态：招聘阅读研究与合成研读记录；当前执行协议以 `references/recruiter-review-protocol.md` 为准。本文不定义发布契约。
- 目标：先学习从业者公开的筛选做法，再让独立 subagent 按固定步骤审阅。不是让模型仅凭“扮演 recruiter”自由打分。

## 1. 已阅读的具名从业者来源

### S1 — Britt Peeples：技术招聘者的实际阅读顺序

[What Recruiters Actually Scan for in the First 30 Seconds of a Resume Review](https://www.ukg.com/blog/life-ukg/what-recruiters-actually-scan-first-30-seconds-resume-review)，2026-06-09。UKG 官方作者介绍列其为 Principal Talent Acquisition Partner，负责 AI/ML、产品和工程招聘。

他先识别当前角色、最近相关工作和规模；由技能栏去经历中核对技术的实际使用，再看职责如何发展、个人做出了什么成果。其目的在于找到值得继续沟通的依据。这个顺序比单纯数关键词更适合本项目。

采用其“技能—经历互相印证”的阅读动作；“最近 1–3 年”和“30 秒”只作为个人实践背景，不设置成机械淘汰线。较早经历仍可能证明当前 JD 的核心能力；没有指标也可以有具体成果。

### S2 — Gergely Orosz：技术招聘经理的分流与校准

[Advice for Hiring Managers on Running a Good Resume Screening Process](https://thetechresume.com/samples/advice-for-hiring-managers)，作者书籍官网公开章节，页面未给出该章更新日期。角色是工程招聘经理/作者，不能写成专职 recruiter；章内另有具名招聘者访谈。

采用 Yes / Maybe / No 分流，明确岗位真正不能让步的要求，并通过独立阅读后的比较校准标准。其例子提示：不熟悉的技术栈、非线性职业路径和学历替代经历需要结合岗位解释，不能自动归入 No。

本项目借鉴的是保留不确定性和校准流程，不能擅自放宽 JD 明确写出的要求。页面中第三方招聘产品及效果数字不用于当前方案。

### S3 — Marton Trencseni：数据科学招聘经理的判断清单

[How I screen CVs](https://bytepawn.com/how-i-screen-cvs.html)，2024-07-01。作者以招聘经理身份介绍自己与 recruiter 合作筛选的经历；招聘数量为作者自述，未独立审计。

采用其“清楚、相关、结果导向”的检查，以及不要因为陌生学校、陌生公司或工作空档就否定候选人的做法。他也明确表示最终看整体，并非命中一个信号就拒绝。

不采用其个人的任职时长、senior 年限、技术生态偏好等阈值；也不把拼写问题解释成实际工作能力差。这些分歧说明应提炼有依据的动作，而不是复制某位招聘者的所有偏好。

### S4 — Amy Miller：先理解用人问题，再看证据

[How to read a resume like a hiring manager](https://www.youtube.com/watch?v=piFVDwOsFTk)，2025-10-31，13 分 16 秒。发布于作者自己的 Recruiting in Yoga Pants 频道，其[个人简介](https://www.recruitinginyogapants.com/blog/)自述长期从事技术招聘；本轮未独立验证其雇佣历史。

已完整读取英文自动字幕并复核关键段落，未观看视频画面。[07:00](https://www.youtube.com/watch?v=piFVDwOsFTk&t=420s) 起讲 recruiter 如何与 hiring manager 一起看简历、听取逐行反馈；[10:13](https://www.youtube.com/watch?v=piFVDwOsFTk&t=613s) 起讲先从 JD 理解要解决的问题，再找简历里的成果和实际工具使用。自动字幕可能有词误，本文仅作语义转述。

她的 [AMA Friday Y’All!](https://www.recruitinginyogapants.com/ama-friday-yall/)（2020-01-03）还区分最低要求与偏好。采用该区分，不引用旧文对当前 ATS 行为的概括。没有真实 hiring manager 反馈时，只能声称基于公开 JD 建立标准，不能声称已完成雇主内部校准。

## 研究结论与当前契约

- 按原始 JD 区分必需与偏好，保留 AND/OR 条件，不自行添加招聘门槛。
- 先记录简历实际传达的定位与疑问，再核对完整证据、相关经历与遗漏。
- 技能关键词不等于实践；相关行为不足以证明未明确说明的架构、规模、
  生产状态或个人 ownership。
- 陌生雇主、职称变化和职业空档本身不构成失败。建议区分表达问题、
  待候选人确认的事实和真实能力缺口。
- 不把缺少某项展示等同于候选人不会，也不输出面试概率或统一 ATS 分数。

这些是具名从业者的实践与本项目推导，不能证明自动 reviewer 与真人判断
一致。当前独立审查、完整证据复核、同源 DOCX/PDF 视觉检查与发布条件
以 `references/recruiter-review-protocol.md` 为准。本文提供研究依据，不作为
另一份执行协议或发布门禁。
