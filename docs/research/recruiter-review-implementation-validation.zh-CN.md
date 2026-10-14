# Recruiter Review 实现验证

验证日期：2026-09-18 UTC。范围为 Issue #1 的项目内实现，保留此前的 Resume Generation Record 工作；不修改 PDF 发布事务或共享安装。

## 确定性验证

- 现有质量报告 CLI 增加可选审阅输入，旧调用保持兼容。
- 新增 16 个入口测试，使用临时外部 workspace、实际 PDF、事实账本和 manifest，覆盖版本过期、错误引用、冻结阶段被改写、缺失/无效数据、文字/自审降级、结构错误及现有 QA 不可被正面意见覆盖。
- 全量测试：145 个通过；`ruff check scripts templates tests` 通过；官方 `skills-ref validate` 通过，工具版本沿用 CI 固定提交。
- 本地测试解释器：Python 3.14；本轮没有运行 GitHub CI 的 Python 3.9/3.12 矩阵。
- 独立只读代码审阅未发现阻断问题，并进行了 682 个内存字段类型变异检查；该检查不替代真实 PDF 的入口测试。

## 独立两阶段演练

使用新的独立上下文 agent，只提供协议、原始 JD 和从真实生成 PDF 提取的分页文字。不给它预期答案、作者历史或隐藏账本。Phase A 先返回，由宿主保存后再请求 Phase B。两例均以真实响应组装报告，经过完整质量报告 CLI 校验，返回码为 0。

| 虚构案例 | 观察到的意见 | 证据处理 |
| --- | --- | --- |
| Python 后端符合，但 Kubernetes 仅本地原型；JD 要求生产操作 | Maybe | Python demonstrated；生产 Kubernetes partial；未把原型升级成生产经验 |
| JD 要求 Python 或 Go，Kafka 为偏好；简历有 Python API 工作 | Yes | 保留 OR 逻辑；Kafka not_shown 不阻止继续沟通 |

样本来自版本化的通用评估案例。标签是开发期暂定预期，没有真人 recruiter 标注；这两例各执行一次，未统计准确率、延迟或 token 开销。两次均是 `text_only`，没有把它们称为真实候选人的视觉终审。

## 当前边界

- 编排由宿主执行；Python 校验器不调用模型，也不负责发布。
- 哈希与引文存在性不能证明模型已完整提取 JD、严格推理或实际保持了所有行为约束。
- 多服务语义回归和文档指令注入案例已保留，未在本轮新的独立 agent 中重跑。更广泛的判断一致性、对照布局案例与真人评估仍是后续工作。
- 生产调用流程以 `references/recruiter-review-protocol.md` 为权威；历史研究文档描述调研过程，不代替执行协议。
