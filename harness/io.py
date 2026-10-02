"""工件读写与元数据。

职责：确定性、可测试的文件读写（不经 LLM），
工件落盘到 workspace/artifacts/<role>/，并记录元数据（含证据版本绑定）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from .config import PROJECT_ROOT

ARTIFACTS_DIR = PROJECT_ROOT / "workspace" / "artifacts"


class ArtifactMeta(TypedDict):
    """工件元数据。"""

    role: str
    produced_at: str
    based_on: str
    model: str


class WorkspaceIO:
    """确定性文件读写。"""

    def __init__(self, root: Path = ARTIFACTS_DIR):
        self.root = root

    def artifact_path(self, role: str) -> Path:
        return self.root / role / f"{role}.md"

    def read_artifact(self, role: str) -> str:
        p = self.artifact_path(role)
        if not p.exists():
            raise FileNotFoundError(f"工件不存在：{p}")
        return p.read_text(encoding="utf-8")

    def write_artifact(self, role: str, content: str, based_on: str, model: str) -> str:
        """写入工件并返回路径。"""
        p = self.artifact_path(role)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

        meta: ArtifactMeta = {
            "role": role,
            "produced_at": datetime.now(timezone.utc).isoformat(),
            "based_on": based_on,
            "model": model,
        }
        meta_path = self.root / role / "meta.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(p)

    @staticmethod
    def sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
