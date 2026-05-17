from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# --- LIMITS (formerly config/limits.py) ---

MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
MAX_CONTENT_SCAN_BYTES: int = 100_000  # 100 KB
MAX_TEXT_CHUNK_BYTES: int = 1024 * 1024  # 1 MB

# Threading
MAX_WORKERS: int = 16
MEMORY_SAFETY_FACTOR: int = 2

# UI Limits
MAX_CONSOLE_LINES: int = 2000
LOG_ROTATION_BYTES: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 3

# Database
DB_WAL_MODE: bool = True
DB_FOREIGN_KEYS: bool = True

# Scan Defaults
DEFAULT_WORKERS: int = 4
DEFAULT_MAX_OUTPUT_FILES: int = 5
DEFAULT_CHUNK_SIZE_MB: float = 10.0


# --- CONFIG (formerly config/settings.py) ---

class ScanConfig(BaseModel):
    model_config = ConfigDict(frozen=False)
    root: Path
    output_dir: Optional[Path] = None
    error_file: Optional[Path] = None
    mode: str = Field("single", pattern="^(single|multi|chunked)$")

    max_output_files: int = Field(5, ge=1)
    max_chunk_mb: float = Field(10.0, gt=0.0)
    footer_reserve_bytes: int = Field(512, ge=0)
    auto_calc: bool = False
    follow_links: bool = False
    ignore_file_name: str = ".scanignore"
    dry_run: bool = False
    resume: bool = False
    progress: bool = True
    allow_large_files: bool = True
    verbose: bool = False
    skip_hidden: bool = True
    state_file_name: str = Field(".scan_state.json", min_length=1)
    cache_file_name: str = Field(".scan_cache.json", min_length=1)
    index_json_name: str = Field("index.json", min_length=1)
    index_md_name: str = Field("index.md", min_length=1)
    incremental: bool = False
    ignore_patterns: List[str] = Field(default_factory=list)
    search_patterns: List[str] = Field(default_factory=list)
    simple_output: bool = False
    compress: bool = False
    log_file_name: str = Field("scan.log", min_length=1)
    workers: int = Field(1, ge=1)


    @field_validator("root", mode="before")
    @classmethod
    def validate_root(cls, v: Any) -> Path:
        p = Path(v).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"root directory does not exist: {p}")
        return p

    @model_validator(mode="after")
    def compute_derived_paths(self) -> "ScanConfig":
        if self.output_dir is None:
            self.output_dir = self.root / "scan_output"
        else:
            self.output_dir = self.output_dir.expanduser().resolve()
        
        if self.error_file is None:
            self.error_file = self.output_dir / "error.log"
            
        return self

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_path: Optional[Path] = None
    ) -> "ScanConfig":
        if "root" not in data:
            raise ValueError("root is required in config")

        root_path = Path(data["root"]).expanduser()
        if not root_path.is_absolute() and base_path:
            root_path = base_path / root_path
        
        data["root"] = root_path

        if "output_dir" in data and data["output_dir"]:
            out_path = Path(data["output_dir"]).expanduser()
            if not out_path.is_absolute() and base_path:
                out_path = base_path / out_path
            data["output_dir"] = out_path

        return cls(**data)

    @classmethod
    def load_config(
        cls, config_path: Path, base_path: Optional[Path] = None
    ) -> "ScanConfig":
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        ext = config_path.suffix.lower()
        data: Dict[str, Any] = {}

        if ext in (".yaml", ".yml"):
            if not YAML_AVAILABLE:
                raise ImportError(
                    "PyYAML not installed. Install with: pip install pyyaml"
                )
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        elif ext == ".json":
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {ext}")

        return cls.from_dict(data, base_path or config_path.parent)

    @property
    def max_chunk_bytes(self) -> int:
        return int(self.max_chunk_mb * 1024 * 1024)

    @property
    def safe_chunk_bytes(self) -> int:
        return max(1, self.max_chunk_bytes - self.footer_reserve_bytes)

    @property
    def state_file(self) -> Path:
        return self.output_dir / self.state_file_name

    @property
    def cache_file(self) -> Path:
        return self.output_dir / self.cache_file_name

    @property
    def index_json(self) -> Path:
        return self.output_dir / self.index_json_name

    @property
    def index_md(self) -> Path:
        return self.output_dir / self.index_md_name

    @property
    def log_file(self) -> Path:
        return self.output_dir / self.log_file_name


class ConfigLoader:
    """Load and manage configuration profiles."""
    
    def __init__(self, store=None):
        from antigravity.services.json_store import JSONStore
        self.store = store or JSONStore()
    
    def load_profile(self, profile_id: int) -> Optional[Dict]:
        """Load a config profile by ID."""
        return self.store.get_config_profile(profile_id)
    
    def save_profile(self, name: str, config: Dict, is_default: bool = False) -> Dict:
        """Save a config profile."""
        return self.store.save_config_profile(name, config, is_default)
    
    def get_all_profiles(self) -> List[Dict]:
        """Get all config profiles."""
        return self.store.get_all_config_profiles()
    
    def get_default_profile(self) -> Optional[Dict]:
        """Get the default config profile."""
        return self.store.get_default_config_profile()
    
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a config profile."""
        return self.store.delete_config_profile(profile_id)
