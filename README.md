# 产品研发全流程 Agent Harness

一个本地单机、串行流水线的 Agent Harness，从一条产品想法出发，自动驱动五个角色依次协作，产出从 PRD 到代码骨架的完整研发链。

## 架构总览

| 层 | 技术 | 职责 |
|---|---|---|
| 编排 | LangGraph | 五角色串行流水线 + 工件传递 |
| 模型（前四角色） | `deepseek-chat` | PRD / 需求文档 / 技术方案 / 测试报告 |
| 模型（开发角色） | `deepseek-harness-sdk`（`deepseek-v4-flash`） | 真实写代码 + bash 工具执行 |

五角色串行流水线：

```
产品经理(PM) → 需求分析(BA) → 技术方案(Arch) → 开发(Dev) → 测试(QA)
    PRD         需求文档        技术方案      代码骨架      测试报告
```

**关键设计**：

- **每角色独立上下文**：节点间只流转「工件」，不流转推理历史
- **模型单一配置**：`config/model.yaml` 是唯一装配点，全 Agent 复用
- **混合分层**：LangGraph 做编排（强项），DSH SDK 做真实编码（强项）

## 快速开始

### 1. 环境要求

- Python 3.10+
- macOS 14+ (Apple Silicon) / Linux x64 / Windows x64
- DeepSeek API Key

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
export DEEPSEEK_API_KEY=sk-your-key-here
```

> API Key 只从环境变量读取，绝不写入配置文件或代码（防泄漏、防进 git）。

### 4. 运行

```bash
python main.py --idea "做一个宠物领养小程序"
```

产出工件会写入 `workspace/artifacts/<角色>/`，开发角色代码写入 `workspace/dev-workspace/`。

## 目录结构

```
product-dev-harness/
├── config/                  # 声明式配置（唯一装配点）
│   ├── model.yaml           # 模型配置（改这里全局生效）
│   ├── pipeline.yaml        # 流水线顺序
│   └── roles/               # 五角色 system prompt + 产出模板
├── harness/                 # 运行时宿主（薄封装）
│   ├── config.py            # 装配模型 + 凭证注入
│   ├── context.py           # 独立上下文组装
│   ├── io.py                # 工件读写 + 证据版本绑定
│   ├── lifecycle.py         # pre/post 钩子
│   ├── validate.py          # 确定性校验
│   └── runner.py            # PipelineRunner
├── agents/                  # 角色节点
│   ├── base.py              # 前四角色基类（ChatDeepSeek）
│   └── dev_node.py          # 开发角色（DeepSeekHarness SDK）
├── graph/pipeline.py        # LangGraph 图定义
├── main.py                  # CLI 入口
└── workspace/               # 运行时产物（gitignore）
```

## 自定义

### 改模型

编辑 `config/model.yaml`：

```yaml
model: deepseek-chat            # 前四角色
dsh_model: deepseek-v4-flash    # 开发角色
```

### 改角色或顺序

编辑 `config/pipeline.yaml` 的 `roles` 列表，或在 `config/roles/` 下增删角色 YAML。

## 已知限制与风险（务必阅读）

1. **DSH SDK 是 developer preview**（`0.1.5rc1`），API 可能变动，生产部署请 pin 版本。
2. **DSH 系统提示词限制**：单进程内 `sdk-minimal` 的 system prompt 写死为通用工程师人设，开发角色靠任务 prompt 里塞角色说明绕过，无法在 system 层彻底分离。要彻底分离需多 `dsh_home`（暂未实现）。
3. **开发角色产出边界**：V1 产出「代码骨架 + 实现说明」，不自动跑构建/测试。
4. **工件质量**：校验只做「结构完整」，内容质量需人工抽查。

## 设计文档

完整架构设计见 `../designs/产品研发全流程-agent-harness-design-v2.md`。
