# MonkeyResume

[English](README.md)

将候选人资料导入可复用的本地证据缓存，并按 JD 定制单页英文简历的 Agent
Skill。宿主模型阅读完整原文、理解事实并写作；本地脚本保存来源、检查绑定、
生成可编辑 DOCX 和同源 PDF。

可追溯不等于事实正确。发布需要完整独立内容审查、真实视觉检查和单页 A4
物理 QA。没有证据的岗位要求保留为缺口，不补成经历。

## 安装

```bash
git clone https://github.com/Zhangyinglun/monkey-resume.git ~/Projects/monkey-resume
cd ~/Projects/monkey-resume
python3 -m pip install -r requirements.txt
mkdir -p ~/.agents/skills
ln -s ~/Projects/monkey-resume ~/.agents/skills/monkey-resume
```

渲染还需 LibreOffice、Poppler 和 Carlito 字体，环境限制见
[输出与 QA](references/docx-output.md)。安装或更新 Skill、agent 指令后，退出并重启 OpenCode。

## 在 Agent 中使用

**只导入资料：**提供原始简历、工作笔记或候选人信息文档：

```text
使用 $monkey-resume 将这份资料导入我的候选人缓存，暂不需要 JD 或生成简历。
```

**定制并交付：**提供原始 JD 和候选人资料：

```text
使用 $monkey-resume 根据这个岗位定制简历。独立审查内容并检查实际单页 DOCX/PDF 后再发布，默认交付 DOCX，需要时附 PDF。
```

1. 保存原始字节和有序文本块；模型通读来源，用准确原文摘录提出事实，再提交经校验的导入。
2. 分析原始 JD，匹配完整当前缓存，包括更正、项目归属及重要的较早经历。
3. 只维护一份 draft：`target`、`resume`、`evidence_links`、`omissions`；程序计算 manifest 和指纹，无额外写作计划。
4. `prepare` 冻结草稿、产物哈希、输出名及审查模板。审查者先盲读 JD 与可见简历，再核对完整证据和遗漏；逐页检查实际 DOCX 预览及同源 PDF。
5. `publish` 仅接受当前版本的通过审查与物理 QA。审查或渲染不完整时仅保留候选版本；可处理失败保留既有接受产物及历史。不自动填写 PASS，不用自审批准。

命令与契约见 [SKILL.md](SKILL.md)、[资料导入](references/source-ingestion.md)、
[draft schema](references/resume-working-schema.md)、[审查协议](references/recruiter-review-protocol.md)。

## 个人工作目录

默认 `~/Documents/MonkeyResume`。同一候选人始终使用同一外部 `--workspace`，
个人数据不写入本仓库。

```text
USER_WORKSPACE/
├── cache/candidate-state.json   # 事实账本、Profile 和不可变来源注册表
├── cache/sources/              # 原始字节及带位置的文本块
├── cache/draft.json            # 模型草稿（示例位置）
├── candidates/<uuid>/          # 冻结候选版本、DOCX/PDF、审查模板
├── resume_output/              # 已接受的交付文件
└── resume_history/index.html   # 已接受生成版本的离线目录
```

文档重复导入是幂等的。候选人回答可用可选 `--event-id` 对重试去重；
有来源依据的显式 `reactivate`/`supersedes` 更正保留历史。旧 schema 缓存被拒绝：
有意选择新的外部目录，或另行授权迁移；当前未提供迁移 CLI。

即使只交付 DOCX，接受历史仍保留同源 PDF、审查及候选记录。已知公司、岗位、
招聘链接写入 draft 的 `target`；见[历史维护](references/resume-generation-records.md)。

## 开发检查

```bash
python3 -m pip install -r requirements-dev.txt
skills-ref validate "$PWD"
ruff check scripts templates tests
python3 -m unittest discover -s tests -v
```

## 许可证

[MIT](LICENSE)
