# MonkeyResume

[English](README.md)

> **基于证据的简历定制工具。** 零幻觉生成、声明全流程可追溯、默认交付经验证的单页 A4 DOCX，可选同源 PDF。

MonkeyResume 根据你的真实经历生成岗位定制简历，绝不虚构技能、成果或头衔。每条声明绑定事实账本，无法追溯的内容直接阻断发布。

---

## 快速开始（约 2 分钟）

### 1. 克隆仓库

```bash
git clone https://github.com/Zhangyinglun/monkey-resume.git ~/Projects/monkey-resume
cd ~/Projects/monkey-resume
```

### 2. 安装依赖（Python 3.9+）

```bash
python3 -m pip install -r requirements.txt
```

### 3. 注册为 Agent Skill

```bash
mkdir -p ~/.agents/skills
ln -s ~/Projects/monkey-resume ~/.agents/skills/monkey-resume
```

### 4. 在 AI Agent 中调用

提供现有简历和目标岗位描述 (JD)，发送提示词：

```text
使用 $monkey-resume 根据这个岗位定制我的简历，并生成经过校验的单页 DOCX。
```

---

## 核心特性

- **零虚构生成**：仅从已验证事实写作；缺失的 JD 要求明确标记为缺口（Gap）。
- **全链路可追溯**：每条简历要点均直接映射到对应的 Claim ID 与原始依据。
- **精准岗位匹配**：自动将 JD 需求分类为直接匹配、可迁移或缺失能力。
- **页面几何门禁**：物理排版校验，严格确保单页 A4 呈现，杜绝溢出。
- **安全回滚机制**：构建失败文件自动存入 `rejected/`，保护上一份合格简历不被覆盖。

---

## 5 步处理流程

```text
[1. 来源快照] ➔ [2. 事实账本] ➔ [3. JD 分析] ➔ [4. 规划与草拟] ➔ [5. 审计与发布]
```

1. **来源快照**：将原始简历（`.pdf`, `.docx`, `.md`, `.txt`）转换为不可变快照。
2. **事实账本**：将经历拆解为绑定实体的原子声明（Atomic Claims），支持跨 JD 复用。
3. **JD 分析**：将岗位能力与事实匹配，仅在关键信息缺失时发起定向追问。
4. **规划与草拟**：在 Projection Plan 中选择证据，生成符合招聘语境的精炼要点。
5. **审计与发布**：执行事实完整性审计，渲染 PDF 并通过单页 A4 几何校验后发布。

---

## 数据隔离架构

个人数据与生成的 DOCX/PDF 完全保存在候选人工作目录。CLI 默认使用
`~/Documents/MonkeyResume`；可通过 `--workspace` 指定其他位置：

```text
USER_WORKSPACE/
├── cache/
│   ├── base-resume.json          # 不可变来源快照
│   ├── candidate-evidence.json   # 跨 JD 候选人事实账本
│   ├── jd-analysis.json          # 岗位需求匹配分析
│   ├── resume-working.json       # 当前定制简历数据
│   └── resume-changes.json       # 字段级修改变更记录
└── resume_output/
    ├── Candidate_Resume_Role.docx # 校验通过的可编辑 DOCX
    └── rejected/                 # 未通过门禁的候选文件（自动隔离）
```

---

## 开发与测试

运行完整测试套件：

```bash
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

---

## 许可证

[MIT](LICENSE)


## DOCX-first output / 默认 DOCX

默认交付可编辑 DOCX，保留 `--format pdf` 和 `--format both`。PDF 由同一份 DOCX 经 LibreOffice 转换，不维护两套排版。旧命令显式指定 `.pdf` 仍输出 PDF。需安装 LibreOffice、Poppler 和 Carlito 字体。

Default output is editable DOCX. PDF is exported from the exact same document. See [output and QA guide](references/docx-output.md) for dependencies, compatibility, the pinned Apache-2.0 OpenAI public QA tool, and renderer/font limitations.
