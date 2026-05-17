# Comprehensive Prompt for Rebuilding/Enhancing Antigravity Scanner

## Executive Summary

This document provides a complete analysis of the Antigravity Scanner codebase, identifying all strengths, weaknesses, missing features, technical debt, and opportunities for improvement. Use this as the definitive guide for rebuilding, refactoring, and enhancing the application to production-grade standards.

---

## 1. PROJECT OVERVIEW & CORE GOALS

### 1.1 Purpose
High-performance desktop utility for:
- Scanning massive codebases (100GB+ repositories)
- Extracting readable text content for LLM/RAG/context preparation
- Providing powerful post-scan organization/cleaning tools

### 1.2 Key Non-Functional Requirements (MUST Preserve & Strengthen)
- **Memory Safety**: Handle arbitrarily large directories/files without OOM or crashes (streaming I/O, bounded memory ~few hundred MB max)
- **UI Responsiveness**: Responsive UI during long operations (progress, cancel/resume, real-time logs)
- **Cross-Platform**: Windows primary, macOS/Linux secondary (currently Windows-hardcoded)
- **Production Quality**: Robust error handling, logging, validation, atomic operations, incremental processing
- **No Dummy Data**: Everything dynamic and configurable — no static/hardcoded/mock implementations

---

## 2. COMPLETE CODEBASE ANALYSIS

### 2.1 Current Project Structure

```
/workspace/
├── src/antigravity/
│   ├── __init__.py
│   ├── __main__.py              # GUI entry point
│   ├── cli.py                   # Typer CLI (INCOMPLETE)
│   ├── cli/                     # CLI submodules (commands.py, prompts.py)
│   ├── core/                    # Core business logic
│   │   ├── scanner.py           # DirectoryScanner (475 lines)
│   │   ├── writer.py            # OutputWriter (383 lines)
│   │   ├── filters.py           # FileFilter (232 lines)
│   │   ├── chunk_manager.py     # ChunkManager
│   │   └── __init__.py
│   ├── gui/                     # PyQt6 components
│   │   ├── app.py               # Main window (AntigravityShell)
│   │   ├── theme.py             # Design tokens (dark mode only)
│   │   ├── controllers.py       # AppController
│   │   ├── components.py        # Reusable UI components
│   │   ├── components/          # Component submodules
│   │   └── views/               # View modules
│   │       ├── scanner_view.py
│   │       ├── toolkit_view.py
│   │       ├── history_view.py
│   │       └── settings_view.py
│   ├── models/                  # SQLAlchemy models (MISSING - should exist)
│   ├── services/                # Business services
│   │   ├── database.py          # DB layer (229 lines) ✅ GOOD
│   │   ├── history.py           # Scan history (112 lines) ⚠️ INCOMPLETE
│   │   ├── config.py            # ScanConfig (167 lines)
│   │   ├── settings.py          # App settings (70 lines)
│   │   └── logger.py            # Service logger (58 lines)
│   ├── schemas/                 # Pydantic schemas
│   │   └── config.py            # Config validation (INCOMPLETE)
│   ├── utils/                   # Utilities
│   │   ├── file_utils.py        # File operations (144 lines)
│   │   ├── encoding_utils.py    # Encoding detection (100 lines)
│   │   └── logger.py            # Utility logger (34 lines)
│   ├── tools/                   # Organization toolkit
│   │   ├── file_organizer_toolkit.py (427 lines)
│   │   ├── prefix_files_with_folder.py
│   │   ├── clean_duplicate_suffixes.py
│   │   ├── delete_empty_folders.py
│   │   ├── flatten_nested_files.py
│   │   └── system_cleanup.bat   # ⚠️ WINDOWS ONLY
│   ├── analytics/               # ❌ EMPTY DIRECTORY
│   └── plugins/                 # ❌ EMPTY DIRECTORY
├── tests/
│   ├── test_scanner.py          # Unit tests (494 lines)
│   └── test_services.py         # Service tests (63 lines) ⚠️ MINIMAL
├── build_exe.py                 # ⚠️ WINDOWS-ONLY BUILD
├── AntigravityScanner.spec      # ⚠️ WINDOWS-ONLY PYINSTALLER
├── pyproject.toml               # Package config ✅ GOOD
├── requirements.txt             # Dependencies
├── ruff.toml                    # Linting config
├── setup.cfg                    # Setup config
├── SSOT.md                      # Single Source of Truth ✅ GOOD
├── README.md                    # Documentation
└── .github/workflows/ci.yml     # CI/CD ⚠️ OUTDATED
```

### 2.2 Database Structure (Current)

**Tables Implemented:**
- `scan_records`: Scan history with metrics (files_scanned, files_processed, bytes_processed, elapsed_seconds, status)
- `scan_files`: File-level tracking (relative_path, absolute_path, extension, size_bytes, lines_count, encoding, output_file, processed, skipped, file_hash)
- `scan_config_profiles`: Saved configuration profiles (name, description, config_json, is_default)
- `app_settings`: Application preferences (key, value, value_type, description, category)

**✅ Strengths:**
- SQLAlchemy 2.0+ with type hints (Mapped[])
- WAL mode enabled for SQLite
- Proper relationships with cascade delete
- Strategic indexes on frequently queried columns
- Thread-safe session management

**⚠️ Issues:**
- `history.py` service doesn't utilize `ScanFile` or `ScanConfigProfile` tables
- No analytics queries implemented
- Missing pagination for history retrieval
- No config profile CRUD operations

---

## 3. WHAT SHOULD BE REMOVED

### 3.1 Deprecated/Hardcoded Components

| File/Component | Issue | Action |
|----------------|-------|--------|
| `tools/system_cleanup.bat` | Windows-only batch script | **REMOVE** - Replace with cross-platform Python implementation |
| `build_exe.py` | Hardcoded for Windows (`main.py`, Windows paths) | **REPLACE** - Multi-platform PyInstaller spec generator |
| `AntigravityScanner.spec` | References non-existent `main.py`, old module paths | **REPLACE** - Generate from `build_exe.py` dynamically |
| `.github/workflows/ci.yml` | References old file structure (`scan.py`, `core/scanner.py`) | **REPLACE** - Update to current structure |
| `cli.py` | Stub implementation with no actual logic | **REWRITE** - Full feature parity with GUI |
| `src/antigravity/plugins/` | Empty directory, traces of old plugin system | **REMOVE** or implement proper plugin architecture |
| `src/antigravity/analytics/` | Empty directory | **IMPLEMENT** or remove |
| Old import paths in specs | References `app.views.*` instead of `antigravity.gui.views.*` | **FIX** all references |

### 3.2 Code Smells & Technical Debt

1. **Inconsistent Path Handling**:
   - Some modules use `pathlib.Path`, others use string concatenation
   - `build_exe.py` uses `os.path` instead of `pathlib`

2. **Duplicate Logger Definitions**:
   - `utils/logger.py` (34 lines)
   - `services/logger.py` (58 lines)
   - Inline `logging.getLogger()` calls throughout
   - **Action**: Consolidate into single logging service

3. **Incomplete Type Hints**:
   - `schemas/config.py` has minimal Pydantic models vs comprehensive `services/config.py`
   - Many functions lack return type annotations
   - **Action**: Run mypy strictly, add type hints everywhere

4. **Hardcoded Constants**:
   - Theme tokens only support dark mode
   - MAX_WORKERS=16 hardcoded (should be CPU-based)
   - Default chunk sizes not user-configurable via UI

5. **Error Handling Gaps**:
   - Silent exception swallowing in `history.py` (lines 59-70, 92-95, 103-104, 111-112)
   - No centralized exception handler
   - No user-friendly error messages

---

## 4. MISSING FEATURES (CRITICAL)

### 4.1 Core Scanning Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Multi-format Text Extraction** | P0 | PDF (PyPDF2), DOCX (python-docx), RTF, ODT support |
| **Archive Handling** | P0 | ZIP/TAR extraction with optional recursion depth control |
| **OCR Integration** | P1 | Optional Tesseract OCR for images (png, jpg) containing text |
| **Advanced Binary Detection** | P1 | Magic byte analysis + MIME type detection (python-magic) |
| **Token Estimation** | P1 | Estimate LLM tokens (tiktoken) for context window planning |
| **Content Hashing** | P0 | blake3/xxhash for deduplication and incremental scans |
| **Partial File Resume** | P1 | Track partially processed files for true resume capability |
| **Search Pattern Matching** | P0 | Regex/glob search during scan with match highlighting |

### 4.2 Filtering System Improvements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Gitignore-style Patterns** | P0 | Full .gitignore syntax support (.scanignore) |
| **Regex Filters** | P1 | Custom regex patterns for include/exclude |
| **Size Range Filters** | P0 | Min/max file size filtering (not just max) |
| **Date Range Filters** | P1 | Modified/created date filtering |
| **MIME Type Filters** | P1 | Filter by detected MIME type |
| **Custom Extension Groups** | P0 | Named groups (e.g., "code", "docs", "configs") |
| **Filter Preview** | P1 | Show what would be filtered before scanning |

### 4.3 Organization Toolkit Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Duplicate Detector** | P0 | Content hash or name-based duplicate finding |
| **Bulk Renamer** | P0 | Advanced renaming with patterns, counters, dates |
| **Archive Extractor** | P1 | Extract archives with organized output structure |
| **Conflict Resolution** | P0 | Smart handling for name collisions (rename/overwrite/skip/merge) |
| **Dry-run Mode** | P0 | Preview all changes before applying |
| **Undo/Backup** | P1 | Automatic backup before destructive operations |
| **Chainable Operations** | P1 | Queue multiple operations to run sequentially |
| **Custom Rules Engine** | P2 | User-defined organization rules (JSON/YAML) |

### 4.4 GUI/UX Improvements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Light/Dark Theme Toggle** | P0 | System preference detection + manual override |
| **Analytics Dashboard** | P0 | Charts (matplotlib/Qt Charts): file type pie, size treemap, scan timeline |
| **Searchable History** | P0 | Filter/sort/search scan history with date ranges |
| **Drag & Drop** | P0 | Drag directories onto app window |
| **File Tree Preview** | P1 | Optional tree view for small directories |
| **Progress Estimation** | P0 | ETA calculation with confidence intervals |
| **Cancel/Resume** | P0 | Graceful cancellation with resume capability |
| **System Tray Integration** | P1 | Minimize to tray, background scans |
| **Toast Notifications** | P1 | Completion/error notifications |
| **Accessibility** | P1 | Screen reader support, keyboard navigation, high contrast mode |
| **Multi-window Support** | P2 | Multiple independent scan sessions |

### 4.5 CLI Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Full Feature Parity** | P0 | All GUI features available via CLI |
| **Rich Output** | P0 | Tables, progress bars, syntax highlighting (rich library) |
| **JSON Output Mode** | P0 | Machine-readable output for scripting |
| **Interactive Mode** | P1 | Prompts for missing parameters |
| **Config Profiles** | P1 | Load/save scan configurations |
| **Batch Scripts** | P2 | Run multiple scans from config file |
| **Watch Mode** | P1 | Monitor directory for changes |

### 4.6 AI Integrations

| Feature | Priority | Description |
|---------|----------|-------------|
| **LLM Summarization** | P1 | Post-scan summarization via local (ollama) or API (OpenAI/Anthropic) |
| **Auto-categorization** | P1 | AI-powered file categorization |
| **Smart Chunking** | P2 | Semantic chunking based on content structure |
| **Embedding Generation** | P2 | Optional vector embeddings for RAG pipelines |
| **Token Counting** | P0 | Accurate token estimation for various LLM models |

### 4.7 Automation & Extensibility

| Feature | Priority | Description |
|---------|----------|-------------|
| **Watch Mode** | P1 | FileSystemWatcher for real-time monitoring |
| **Batch Job Queue** | P1 | Queue multiple scans/operations |
| **Python API** | P0 | Scriptable interface for automation |
| **Plugin System** | P2 | Entry points for custom filters/writers/organizers |
| **Webhook Notifications** | P2 | Notify external services on completion |
| **Scheduled Scans** | P2 | Cron-like scheduling |

### 4.8 Monitoring & Analytics

| Feature | Priority | Description |
|---------|----------|-------------|
| **Resource Monitoring** | P1 | Real-time CPU, RAM, I/O dashboard |
| **Scan Metrics** | P0 | Detailed statistics per scan (file types, sizes, errors) |
| **Historical Trends** | P1 | Charts showing scan history over time |
| **Performance Profiling** | P2 | Identify bottlenecks in scan process |
| **Export Reports** | P1 | HTML/PDF/Markdown reports |

---

## 5. SCALABILITY GAPS

### 5.1 Current Limitations

1. **No Distributed Scanning**: Single-machine only
2. **Limited Progress Estimation**: Basic ETA, no confidence intervals
3. **Weak Large-File Handling**: No special handling for GB+ files
4. **Memory Monitoring**: No adaptive worker count based on RAM usage
5. **No Checkpointing**: Long scans can't resume from arbitrary points

### 5.2 Required Improvements

| Improvement | Description |
|-------------|-------------|
| **Adaptive Worker Count** | Monitor RAM usage, reduce workers if approaching limits |
| **Chunked Large Files** | Split GB+ files into manageable chunks |
| **Distributed Hints** | Architecture for future multi-node scanning |
| **Checkpoint Every N Files** | Save state every N files for fine-grained resume |
| **Memory-mapped I/O** | For very large files, use mmap instead of loading into memory |
| **Async I/O** | Use asyncio for better I/O concurrency |

---

## 6. SECURITY ISSUES

### 6.1 Current Protections (✅ Good)
- Path normalization via `pathlib`
- Atomic writes prevent corruption
- Binary file detection

### 6.2 Missing Security Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Output Directory Sandboxing** | P0 | Ensure writes never escape designated output dir |
| **Permission Checks** | P0 | Verify read/write permissions before operations |
| **Symlink Attack Prevention** | P1 | Detect and handle symlink loops/malicious symlinks |
| **Virus Scan Hooks** | P2 | Optional integration with antivirus APIs |
| **Sensitive Data Detection** | P1 | Warn about potential secrets (API keys, passwords) |
| **Audit Logging** | P1 | Log all file operations for compliance |
| **Secure Deletion** | P2 | Secure file deletion options (shred-like) |

---

## 7. PERFORMANCE PROBLEMS

### 7.1 Current Strengths (✅ Keep)
- ThreadPoolExecutor for parallel I/O
- Streaming I/O with 1MB chunks
- Incremental cache via mtime/size
- SQLite WAL mode

### 7.2 Performance Issues to Fix

| Issue | Impact | Solution |
|-------|--------|----------|
| **No Memory Monitoring** | Risk of OOM on large scans | Add psutil monitoring, adaptive workers |
| **Fixed Chunk Size** | Suboptimal for varying file sizes | Dynamic chunk sizing based on file type |
| **Inefficient Cache** | JSON cache slow for large dirs | Use SQLite or binary format (protobuf) |
| **No I/O Prioritization** | Small files wait behind large files | Priority queue for file processing |
| **Blocking UI Updates** | UI lag during heavy logging | Batch log updates, async signal emission |
| **Redundant Stats Calls** | Multiple stat() calls per file | Cache stat results, single call per file |

### 7.3 Optimization Opportunities

1. **Use blake3 Instead of xxhash**: Faster hashing for incremental scans
2. **Memory-mapped File Reading**: For large files (>100MB)
3. **Async Directory Traversal**: Use `aioscan` or similar
4. **Batch Database Writes**: Transaction batching for file-level tracking
5. **Lazy Loading**: Don't load entire file list into memory upfront

---

## 8. ARCHITECTURAL FLAWS

### 8.1 Separation of Concerns

**Current State**: ⚠️ Partial violations
- Core engine mostly UI-agnostic ✅
- Some UI logic leaked into services
- CLI and GUI share some code but not enough

**Required Changes**:
```
IDEAL ARCHITECTURE:

┌─────────────────────────────────────────┐
│              PRESENTATION LAYER          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │   PyQt6 GUI │  │   Typer CLI      │  │
│  └──────┬──────┘  └────────┬─────────┘  │
│         │                  │             │
│         └────────┬─────────┘             │
│                  ▼                       │
│  ┌───────────────────────────────┐      │
│  │      Controllers/ViewModels    │      │
│  └───────────────┬───────────────┘      │
└──────────────────┼──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           APPLICATION LAYER              │
│  ┌─────────────────────────────────┐    │
│  │   Core Engine (UI-Agnostic)     │    │
│  │   - DirectoryScanner            │    │
│  │   - OutputWriter                │    │
│  │   - FileFilter                  │    │
│  │   - OrganizationToolkit         │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────────┐    │
│  │   Services Layer                │    │
│  │   - DatabaseService             │    │
│  │   - HistoryService              │    │
│  │   - SettingsService             │    │
│  │   - LoggingService              │    │
│  └──────────────┬──────────────────┘    │
└──────────────────┼──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│            DOMAIN LAYER                  │
│  ┌─────────────────────────────────┐    │
│  │   Models (SQLAlchemy)           │    │
│  │   - ScanRecord                  │    │
│  │   - ScanFile                    │    │
│  │   - ScanConfigProfile           │    │
│  │   - AppSetting                  │    │
│  └─────────────────────────────────┘    │
│                                          │
│  ┌─────────────────────────────────┐    │
│  │   Schemas (Pydantic)            │    │
│  │   - ScanConfig                  │    │
│  │   - FilterConfig                │    │
│  │   - OrganizerConfig             │    │
│  └─────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

### 8.2 State Management Issues

**Current**: Mix of JSON state files, database, and in-memory state
**Problem**: Inconsistent state, potential for corruption
**Solution**: 
- Single source of truth: SQLite database
- JSON state files only for crash recovery
- Transaction-based state updates
- Event sourcing for audit trail

### 8.3 Error Handling Architecture

**Current**: Ad-hoc try/except blocks, silent failures
**Required**:
```python
# Centralized exception hierarchy
class AntigravityError(Exception):
    """Base exception"""

class ScanError(AntigravityError):
    """Scan-specific errors"""

class OrganizationError(AntigravityError):
    """Organization toolkit errors"""

class ConfigurationError(AntigravityError):
    """Invalid configuration"""

# Global exception handler
def handle_exception(exc: Exception, context: dict):
    """Log, notify user, suggest recovery"""
```

---

## 9. CODE QUALITY & MAINTAINABILITY

### 9.1 Current State

| Metric | Status | Target |
|--------|--------|--------|
| Type Hints | ⚠️ Partial | 100% coverage |
| Docstrings | ⚠️ Inconsistent | All public APIs |
| Test Coverage | ⚠️ ~30% estimated | >80% |
| Linting | ✅ Ruff configured | Enforce in CI |
| Code Style | ✅ Black configured | Enforce in CI |

### 9.2 Required Improvements

1. **Type Hints Everywhere**:
   ```bash
   mypy --strict src/antigravity/
   ```

2. **Comprehensive Docstrings**:
   - Google or NumPy style
   - Include Args, Returns, Raises, Examples

3. **Testing Strategy**:
   - Unit tests: pytest
   - GUI tests: pytest-qt
   - Property-based: hypothesis
   - Integration tests: Full workflow tests
   - Target: >80% coverage

4. **Pre-commit Hooks**:
   ```yaml
   repos:
     - black
     - ruff
     - mypy
     - pytest
   ```

5. **Documentation**:
   - API documentation (Sphinx or MkDocs)
   - User guide (USAGE.md)
   - Changelog (CHANGELOG.md)
   - Contribution guide (CONTRIBUTING.md)

---

## 10. DEPLOYMENT & DEVOPS

### 10.1 Current Issues

| Issue | Problem | Solution |
|-------|---------|----------|
| Windows-only build | `build_exe.py` hardcoded for Windows | Multi-platform PyInstaller specs |
| Outdated CI | References old file structure | Update GitHub Actions workflow |
| No versioning strategy | Version in pyproject.toml only | Git tags + automated versioning |
| No auto-updates | Manual download required | Implement auto-update mechanism |
| No package signing | Security concern | Sign executables for all platforms |

### 10.2 Required Deployment Pipeline

```yaml
# GitHub Actions Workflow
name: Build & Release

on:
  push:
    tags: ['v*']

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
      - checkout
      - setup-python
      - install-deps
      - run-tests (pytest --cov)
      - upload-coverage
  
  build:
    needs: test
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - checkout
      - pyinstaller-build
      - sign-executable
      - upload-artifact
  
  release:
    needs: build
    runs-on: ubuntu-latest
    
    steps:
      - download-artifacts
      - create-github-release
      - publish-to-pypi
```

### 10.3 Environment Variables & Configuration

**Supported Environment Variables**:
```bash
ANTIGRAVITY_CONFIG=/path/to/config.toml  # Custom config path
ANTIGRAVITY_LOG_LEVEL=DEBUG              # Logging level
ANTIGRAVITY_DB_URL=sqlite:///custom.db   # Custom database path
ANTIGRAVITY_CACHE_DIR=/tmp/cache         # Custom cache directory
```

**Configuration Files**:
- `pyproject.toml`: Package metadata, tool configs
- `config.toml` (optional): User configuration profiles
- `.scanignore`: Per-project ignore patterns

---

## 11. UI/UX ENHANCEMENTS

### 11.1 Current UI Analysis

**Strengths**:
- Modern dark theme with design tokens
- Tabbed navigation (Scanner, Toolkit, History, Settings)
- Real-time console log viewer
- Sidebar navigation

**Weaknesses**:
- Dark mode only (no light theme)
- No accessibility features
- Limited customization
- No system tray integration
- No notifications

### 11.2 Required UI Improvements

1. **Theming System**:
   ```python
   class ThemeManager:
       def __init__(self):
           self.themes = {
               'dark': DARK_THEME,
               'light': LIGHT_THEME,
               'system': detect_system_theme()
           }
       
       def apply_theme(self, theme_name: str):
           # Apply QSS dynamically
   ```

2. **Accessibility**:
   - ARIA-like labels for screen readers
   - Keyboard shortcuts for all actions
   - High contrast mode
   - Adjustable font sizes
   - Focus indicators

3. **Dashboard Enhancements**:
   - Real-time resource usage graphs
   - File type distribution charts
   - Scan progress with ETA
   - Recent scans quick access
   - Quick actions panel

4. **Settings Overhaul**:
   - Organized categories (General, Scan, Organization, Advanced)
   - Search functionality
   - Import/export settings
   - Reset to defaults
   - Profile management

---

## 12. INTEGRATION REQUIREMENTS

### 12.1 External Services/APIs

| Integration | Purpose | Priority |
|-------------|---------|----------|
| **OpenAI API** | LLM summarization | P1 |
| **Anthropic API** | Alternative LLM | P1 |
| **Ollama** | Local LLM inference | P1 |
| **GitHub** | Repository scanning | P2 |
| **GitLab** | Repository scanning | P2 |
| **VirusTotal** | Malware scanning | P2 |
| **Tesseract** | OCR for images | P1 |

### 12.2 File Format Support

**Currently Supported**:
- Plain text files ✅
- Source code files ✅

**Missing Support**:
- PDF (PyPDF2, pdfplumber)
- DOCX (python-docx)
- RTF (striprtf)
- ODT (odfpy)
- EPUB (ebooklib)
- ZIP/TAR/GZ/BZ2 (tarfile, zipfile)
- Images with text (PIL + Tesseract)

---

## 13. DETAILED FEATURE SPECIFICATIONS

### 13.1 Enhanced Scanning System

**What it does**: Scans directories, extracts text, applies filters, writes output

**Inputs**:
- UI: Directory picker, mode selector, filter options, worker count
- CLI: Arguments and flags
- DB: Saved config profiles
- API: Programmatic configuration

**Outputs**:
- Text files (single/multi/chunked)
- Metadata JSON (index.json)
- Error log (error.log)
- Database records (ScanRecord, ScanFile)
- Console logs (real-time)

**Backend Logic**:
```python
class DirectoryScanner:
    def __init__(self, config: ScanConfig):
        self.config = config
        self.filter = FileFilter(config)
        self.writer = OutputWriter(config)
        self.metrics = ScanMetrics()
    
    def scan(self) -> ScanMetrics:
        # 1. Enumerate candidates (streaming, not all in memory)
        # 2. Apply filters
        # 3. Process files (thread pool)
        # 4. Write output (atomic, chunked)
        # 5. Update database
        # 6. Return metrics
```

**Error Handling**:
- Permission errors: Log and skip
- Encoding errors: Try multiple encodings, then skip
- Disk full: Graceful stop, cleanup partial files
- Interrupted: Save state, allow resume

**Progress/Resume**:
- Progress callbacks every N files
- State saved every N files (configurable)
- Hash-based incremental cache
- Partial file tracking for true resume

### 13.2 Organization Toolkit

**What it does**: Restructures directories, renames files, cleans up

**Operations**:
1. **Prefixer**: Add/remove parent folder name as prefix
2. **Cleaner**: Remove numeric suffixes (_001, (1), etc.)
3. **Purger**: Remove empty folders (with safety checks)
4. **Flattener**: Move files up levels or full flatten
5. **Pattern Mover**: Group files by regex patterns
6. **Duplicate Detector**: Find duplicates by hash or name
7. **Bulk Renamer**: Advanced renaming with patterns

**Inputs**:
- Target directory
- Operation type
- Operation-specific parameters
- Dry-run flag
- Backup flag

**Outputs**:
- Modified directory structure
- Operation log (what was changed)
- Backup archive (if enabled)
- Database record of operation

**Backend Logic**:
```python
class OrganizationToolkit:
    def __init__(self, target: Path, dry_run: bool = False):
        self.target = target
        self.dry_run = dry_run
        self.changes = []
    
    def prefix_files(self, pattern: str) -> List[Change]:
        # Implementation
    
    def flatten(self, max_depth: int = None) -> List[Change]:
        # Implementation
    
    def execute(self) -> bool:
        if self.dry_run:
            return True
        # Apply all changes with rollback on error
```

**Error Handling**:
- Name conflicts: Configurable resolution (skip/rename/overwrite)
- Permission errors: Log and continue
- Disk space: Check before operations
- Rollback on critical errors

### 13.3 Analytics Dashboard

**What it does**: Visualizes scan data and historical trends

**Components**:
1. **File Type Distribution**: Pie chart of extensions
2. **Size Distribution**: Histogram/treemap of file sizes
3. **Scan Timeline**: Line chart of scans over time
4. **Performance Metrics**: Bar chart of scan durations
5. **Error Analysis**: Table of common errors

**Data Sources**:
- SQLite database (ScanRecord, ScanFile tables)
- Real-time scan metrics
- Aggregated statistics

**Backend Logic**:
```python
class AnalyticsService:
    def get_file_type_distribution(self, scan_id: int = None) -> dict:
        # Query database, aggregate by extension
    
    def get_size_distribution(self, scan_id: int = None) -> dict:
        # Bucket files by size ranges
    
    def get_scan_timeline(self, days: int = 30) -> list:
        # Time-series data for charts
    
    def generate_report(self, format: str = 'html') -> str:
        # Generate HTML/PDF/Markdown report
```

---

## 14. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (MVP Refactor) - Weeks 1-2

**Goals**: Clean structure, working core, basic UI, CLI foundation

**Tasks**:
- [ ] Fix project structure (move models/, create proper packages)
- [ ] Complete core engine refactoring (scanner, writer, filters)
- [ ] Implement full database service (history, config profiles)
- [ ] Basic CLI with feature parity
- [ ] Fix build system for cross-platform
- [ ] Update CI/CD pipeline
- [ ] Add comprehensive type hints
- [ ] Set up pre-commit hooks

**Deliverables**:
- Working CLI and GUI
- Cross-platform builds
- >50% test coverage
- Updated documentation

### Phase 2: Core Features - Weeks 3-4

**Goals**: All scan modes, organization tools, robust error handling

**Tasks**:
- [ ] Implement all scan modes (single, multi, chunked)
- [ ] Complete organization toolkit (all 7 operations)
- [ ] Advanced filtering (regex, MIME, size ranges)
- [ ] Incremental scanning with hash cache
- [ ] Resume functionality with partial file tracking
- [ ] Comprehensive error handling and recovery
- [ ] Logging overhaul (structured, rotating)
- [ ] Progress estimation improvements

**Deliverables**:
- Full-featured scanner
- Complete organization toolkit
- Robust error handling
- >70% test coverage

### Phase 3: Polish & UX - Weeks 5-6

**Goals**: Theming, analytics, notifications, accessibility

**Tasks**:
- [ ] Light/dark theme toggle
- [ ] Analytics dashboard with charts
- [ ] Searchable/filterable history
- [ ] System tray integration
- [ ] Toast notifications
- [ ] Accessibility features (keyboard nav, screen reader)
- [ ] Drag & drop support
- [ ] Settings overhaul with profiles
- [ ] CLI rich output

**Deliverables**:
- Polished UI
- Analytics dashboard
- Full accessibility
- >80% test coverage

### Phase 4: Advanced & Extensibility - Weeks 7-8

**Goals**: AI integrations, plugins, automation, watch mode

**Tasks**:
- [ ] AI summarization hooks (local + API)
- [ ] Token estimation
- [ ] Plugin system architecture
- [ ] Watch mode (filesystem monitoring)
- [ ] Batch job queue
- [ ] Python API for scripting
- [ ] Export reports (HTML/PDF)
- [ ] Multi-format text extraction (PDF, DOCX, etc.)
- [ ] Archive handling

**Deliverables**:
- AI integrations
- Plugin system
- Automation capabilities
- Extended format support

### Phase 5: Optimization & Release - Weeks 9-10

**Goals**: Performance tuning, security audit, final release

**Tasks**:
- [ ] Performance profiling and optimization
- [ ] Memory monitoring and adaptive workers
- [ ] Security audit (path traversal, permissions)
- [ ] Code signing for all platforms
- [ ] Auto-update mechanism
- [ ] Final documentation pass
- [ ] Beta testing program
- [ ] Production release

**Deliverables**:
- Optimized performance
- Security hardened
- Production-ready release
- Complete documentation

---

## 15. SUCCESS CRITERIA

### Functional Requirements
- [ ] Scan 100GB+ repository without OOM
- [ ] Maintain <500MB memory footprint
- [ ] UI remains responsive during scans
- [ ] Resume interrupted scans seamlessly
- [ ] All features available in both GUI and CLI
- [ ] Cross-platform executables (Win/macOS/Linux)

### Quality Requirements
- [ ] >80% test coverage
- [ ] Zero mypy type errors
- [ ] All linting checks pass
- [ ] Comprehensive documentation
- [ ] User-friendly error messages
- [ ] Graceful degradation on errors

### Performance Requirements
- [ ] Scan speed: >100 files/second (SSD)
- [ ] Startup time: <2 seconds
- [ ] Memory usage: <500MB for typical scans
- [ ] CPU usage: Configurable (default 50-75%)

### Security Requirements
- [ ] No path traversal vulnerabilities
- [ ] Proper permission checks
- [ ] Safe file deletion (no accidental data loss)
- [ ] Audit logging for compliance
- [ ] Secure credential storage (for API keys)

---

## 16. FINAL CHECKLIST

### Before Starting Development
- [ ] Review and understand this entire document
- [ ] Set up development environment
- [ ] Install pre-commit hooks
- [ ] Run existing tests to establish baseline
- [ ] Create feature branches for each phase

### During Development
- [ ] Write tests first (TDD where possible)
- [ ] Maintain type hints
- [ ] Update documentation as you go
- [ ] Commit frequently with clear messages
- [ ] Run linters before committing

### Before Each Release
- [ ] Run full test suite
- [ ] Check test coverage
- [ ] Run mypy strict check
- [ ] Test on all target platforms
- [ ] Update CHANGELOG.md
- [ ] Tag release with semantic version

---

## CONCLUSION

This comprehensive prompt outlines everything needed to rebuild and enhance the Antigravity Scanner into a production-grade, maintainable, scalable, and extensible desktop utility. Follow the phased roadmap, prioritize based on the stated criteria, and maintain focus on the core goals: **performance**, **reliability**, and **user experience**.

Key principles to remember:
1. **No dummy data** - Everything must be dynamic and configurable
2. **Cross-platform first** - Design for Win/macOS/Linux from the start
3. **Test-driven** - Write tests before or alongside features
4. **User-centric** - Prioritize features that improve user experience
5. **Performance matters** - Profile early, optimize often
6. **Security by design** - Never compromise on safety

Good luck with the rebuild! 🚀
