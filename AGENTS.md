# OpenMontage

**MANDATORY: Read `AGENT_GUIDE.md` before responding to ANY user message.**

Do not act on the user's request until you have read AGENT_GUIDE.md.
It contains routing rules that determine your first action based on what the user asked.
Skipping it WILL cause you to take the wrong action.

There are no instructions in this file. All instructions are in AGENT_GUIDE.md.

## Tooling Preference

When exploring or modifying code, prefer `codegraph_explore` over manual grep/Read — it returns relevant source with call paths and blast radius in one round-trip.

## 回复语言规则（Reply Language Rules）

- **默认使用简体中文回复用户。** 除非用户明确要求使用英文，否则所有交流语言为中文。
- **保持简洁直接。** 不加套话、状态更新或冗长前言。遇到疑问时先问一个问题，给出结论前先给出判断。
- **技术名词保留原文。** 专有名词（pipeline 名称、`cinematic`、`Remotion`、`HyperFrames`、工具名、文件路径）使用原文或半角；解释这些名词时再用中文。
- **决策过程不变。** 中文回复前提下，所有英文版本定义的工作流、质量门、审批流程、预检与检查步骤照常执行 — 语言不影响治理逻辑。
- **语气风格。** 作为工程编排者，用判断性语气陈述路由决策：说明检测到何种意图、为什么选择该路径，避免职守气或客套话。

## 文档编写规则（Documentation Language Rules）

- 由本 agent 编写或翻译的 Markdown 设计文档、技术文档、pipeline 说明等（例如 `docs/superpowers/` 下的设计稿）使用**简体中文**撰写。
- 代码文件（`.py` / `.yaml` / `.json`）、JSON schema 以及面向工程协作的接口约定，**保持为英文 / 原文**，不翻译。
- 技术专有名词（pipeline 名称、工具名、文件路径、provider 名称）**保留原文**。
