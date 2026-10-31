"""Runtime configuration, read once from environment variables.

Nothing here points at a remote service: the model runs on the local machine (Ollama) and
all data is stored under RELIEF_VAR_DIR.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Read KEY=VALUE lines from <project>/.env into the environment (real environment variables win)."""
    f = ROOT / ".env"
    if not f.is_file():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _path(name: str, default: str) -> Path:
    p = Path(_env(name, default))
    return p if p.is_absolute() else ROOT / p


@dataclass(frozen=True)
class Settings:
    llm_host: str = field(default_factory=lambda: _env("RELIEF_LLM_HOST", "http://localhost:11434"))
    llm_model: str = field(default_factory=lambda: _env("RELIEF_LLM_MODEL", "qwen3:8b"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("RELIEF_LLM_TIMEOUT_S", "120")))
    embedder: str = field(default_factory=lambda: _env("RELIEF_EMBEDDER", "bge"))
    data_dir: Path = field(default_factory=lambda: _path("RELIEF_DATA_DIR", "data"))
    var_dir: Path = field(default_factory=lambda: _path("RELIEF_VAR_DIR", "var"))
    registry_path: Path = field(default_factory=lambda: _path("RELIEF_REGISTRY_PATH", "data/registry/registry.json"))
    api_host: str = field(default_factory=lambda: _env("RELIEF_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(_env("RELIEF_API_PORT", "8000")))
    api_url: str = field(default_factory=lambda: _env("RELIEF_API_URL", "http://127.0.0.1:8000"))
    api_key: str = field(default_factory=lambda: _env("RELIEF_API_KEY", ""))
    max_upload_mb: int = field(default_factory=lambda: int(_env("RELIEF_MAX_UPLOAD_MB", "10")))
    embed_model: str = field(default_factory=lambda: _env("RELIEF_EMBED_MODEL", "nomic-embed-text"))
    jwt_secret: str = field(default_factory=lambda: _env("RELIEF_JWT_SECRET", ""))
    token_hours: float = field(default_factory=lambda: float(_env("RELIEF_TOKEN_HOURS", "10")))
    cors_origins: str = field(default_factory=lambda: _env("RELIEF_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,*"))
    frontend_dist: Path = field(default_factory=lambda: _path("RELIEF_FRONTEND_DIST", "frontend/dist"))
    max_revisions: int = 2
    max_tool_steps: int = 12

    @property
    def secret_path(self) -> Path:
        return self.var_dir / "jwt.secret"

    @property
    def rules_dir(self) -> Path:
        return self.data_dir / "rules"

    @property
    def db_path(self) -> Path:
        return self.var_dir / "relief.sqlite"

    @property
    def checkpoint_path(self) -> Path:
        return self.var_dir / "checkpoints.sqlite"

    @property
    def chroma_dir(self) -> Path:
        return self.var_dir / "chroma"

    @property
    def upload_dir(self) -> Path:
        return self.var_dir / "uploads"


def get_settings() -> Settings:
    """Fresh settings from the current environment (cheap; call where needed)."""
    return Settings()
