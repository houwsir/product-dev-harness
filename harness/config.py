"""配置加载与校验。

职责：读取 config/ 下的 YAML，装配成强类型配置对象，
并在进程边界注入凭证（API Key 从环境变量读取，绝不进配置/上下文）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# 项目根目录（本文件位于 harness/，根目录是上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
ROLES_DIR = CONFIG_DIR / "roles"


class ModelConfig(BaseModel):
    """模型配置（单一来源）。"""

    model: str = "deepseek-chat"
    api_base: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 16000

    # 开发角色（DSH SDK）参数
    dsh_model: str = "deepseek-v4-flash"
    dsh_provider: str = "deepseek-official"
    dsh_max_tokens: int = 49152
    dsh_profile: str = "sdk-minimal"


class RoleConfig(BaseModel):
    """单角色配置。"""

    name: str
    system_prompt: str
    output_template: str = ""


class PipelineConfig(BaseModel):
    """流水线配置。"""

    roles: list[str]


class HarnessParams(BaseModel):
    """开发角色 DSH SDK 的构造参数。"""

    provider: str
    model: str
    max_tokens: int
    cwd: str
    dsh_home: str
    profile: str


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_model_config(path: str | None = None) -> ModelConfig:
    p = Path(path) if path else CONFIG_DIR / "model.yaml"
    return ModelConfig(**_read_yaml(p))


def load_pipeline(path: str | None = None) -> PipelineConfig:
    p = Path(path) if path else CONFIG_DIR / "pipeline.yaml"
    return PipelineConfig(**_read_yaml(p))


def load_role_config(name: str) -> RoleConfig:
    p = ROLES_DIR / f"{name}.yaml"
    return RoleConfig(**_read_yaml(p))


def load_all_roles(pipeline: PipelineConfig) -> dict[str, RoleConfig]:
    return {name: load_role_config(name) for name in pipeline.roles}


def get_api_key() -> str:
    """从环境变量读取 API Key，缺省时抛出明确错误。"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "未找到 DEEPSEEK_API_KEY 环境变量。"
            "请先 export DEEPSEEK_API_KEY=sk-xxx 或使用 .env 文件。"
        )
    return key


def build_chat_model(cfg: ModelConfig):
    """装配前四角色使用的 ChatDeepSeek。凭证从环境变量注入。"""
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(
        model=cfg.model,
        api_key=get_api_key(),
        base_url=cfg.api_base,  # 注意：正确参数名是 base_url，不是 api_base
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )


def build_harness_params(cfg: ModelConfig) -> HarnessParams:
    """装配开发角色 DSH SDK 的构造参数（隔离 home 与 workspace）。"""
    workspace = PROJECT_ROOT / "workspace" / "dev-workspace"
    dsh_home = PROJECT_ROOT / ".dsh-home"
    workspace.mkdir(parents=True, exist_ok=True)
    dsh_home.mkdir(parents=True, exist_ok=True)
    return HarnessParams(
        provider=cfg.dsh_provider,
        model=cfg.dsh_model,
        max_tokens=cfg.dsh_max_tokens,
        cwd=str(workspace.resolve()),
        dsh_home=str(dsh_home.resolve()),
        profile=cfg.dsh_profile,
    )
