from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from pathlib import Path

class FilterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ignore_files: List[str] = Field(default_factory=lambda: [".scanignore"])
    skip_hidden: bool = True
    skip_binary: bool = True
    max_file_size_mb: int = 100
    allowed_extensions: Optional[List[str]] = None

class ScanConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_dir: Path
    output_dir: Path
    mode: str = Field(default="single", pattern="^(single|multi|chunked)$")
    workers: int = Field(default=4, ge=1, le=32)
    filters: FilterConfig = Field(default_factory=FilterConfig)
    gzip_output: bool = False
    incremental: bool = True
