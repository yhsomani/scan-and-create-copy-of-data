"""
JSON-based persistent storage service.
Replaces SQLite database with file-based JSON storage for portability and simplicity.
Thread-safe with file locking.
"""

import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
import hashlib


class JSONStore:
    """Thread-safe JSON file storage with atomic operations."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.scans_file = self.data_dir / "scans.json"
        self.files_file = self.data_dir / "scan_files.json"
        self.configs_file = self.data_dir / "config_profiles.json"
        self.settings_file = self.data_dir / "app_settings.json"
        self.cache_file = self.data_dir / "incremental_cache.json"
        
        # Locks for thread safety
        self._locks = {
            'scans': threading.RLock(),
            'files': threading.RLock(),
            'configs': threading.RLock(),
            'settings': threading.RLock(),
            'cache': threading.RLock(),
        }
        
        # Initialize files if they don't exist
        self._init_files()
    
    def _init_files(self):
        """Initialize JSON files with empty structures if they don't exist."""
        defaults = {
            self.scans_file: {"scans": [], "next_id": 1},
            self.files_file: {"files": [], "next_id": 1},
            self.configs_file: {"profiles": [], "next_id": 1},
            self.settings_file: {"settings": {}},
            self.cache_file: {"cache": {}, "last_cleanup": None},
        }
        
        for file_path, default_data in defaults.items():
            if not file_path.exists():
                self._write_json(file_path, default_data)
    
    @contextmanager
    def _lock(self, store_type: str):
        """Context manager for thread-safe access."""
        lock = self._locks.get(store_type, threading.RLock())
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
    
    def _read_json(self, file_path: Path) -> Dict:
        """Read JSON file with error handling."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # Corrupted file - backup and recreate
            backup_path = file_path.with_suffix('.json.bak')
            shutil.copy(file_path, backup_path)
            print(f"Warning: {file_path} corrupted, restored from backup or reset")
        
        # Return default structure based on file
        if file_path == self.scans_file:
            return {"scans": [], "next_id": 1}
        elif file_path == self.files_file:
            return {"files": [], "next_id": 1}
        elif file_path == self.configs_file:
            return {"profiles": [], "next_id": 1}
        elif file_path == self.settings_file:
            return {"settings": {}}
        elif file_path == self.cache_file:
            return {"cache": {}, "last_cleanup": None}
        return {}
    
    def _write_json(self, file_path: Path, data: Dict):
        """Write JSON file atomically."""
        temp_path = file_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            temp_path.replace(file_path)
        except IOError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def _generate_id(self, data: Dict) -> int:
        """Generate next available ID."""
        return data.get('next_id', 1)
    
    def _increment_id(self, data: Dict):
        """Increment next ID counter."""
        data['next_id'] = data.get('next_id', 1) + 1
    
    # ==================== SCAN RECORDS ====================
    
    def create_scan(self, config: Dict) -> Dict:
        """Create a new scan record."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            
            scan_id = self._generate_id(data)
            now = datetime.utcnow().isoformat()
            
            scan_record = {
                'id': scan_id,
                'status': 'pending',
                'created_at': now,
                'updated_at': now,
                'started_at': None,
                'completed_at': None,
                'source_paths': config.get('source_paths', []),
                'output_dir': config.get('output_dir', ''),
                'scan_mode': config.get('scan_mode', 'multi'),
                'config_json': config,
                'files_scanned': 0,
                'lines_processed': 0,
                'bytes_processed': 0,
                'errors_count': 0,
                'warnings_count': 0,
                'error_messages': [],
                'progress_percent': 0.0,
                'estimated_time_remaining': None,
            }
            
            data['scans'].append(scan_record)
            self._increment_id(data)
            self._write_json(self.scans_file, data)
            
            return scan_record
    
    def update_scan(self, scan_id: int, updates: Dict) -> Optional[Dict]:
        """Update scan record fields."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            
            for scan in data['scans']:
                if scan['id'] == scan_id:
                    scan.update(updates)
                    scan['updated_at'] = datetime.utcnow().isoformat()
                    self._write_json(self.scans_file, data)
                    return scan
            
            return None
    
    def start_scan(self, scan_id: int) -> Optional[Dict]:
        """Mark scan as started."""
        return self.update_scan(scan_id, {
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'progress_percent': 0.0
        })
    
    def complete_scan(self, scan_id: int, stats: Dict) -> Optional[Dict]:
        """Mark scan as completed."""
        updates = {
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
            'progress_percent': 100.0,
        }
        updates.update(stats)
        return self.update_scan(scan_id, updates)
    
    def fail_scan(self, scan_id: int, error_message: str) -> Optional[Dict]:
        """Mark scan as failed."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            
            for scan in data['scans']:
                if scan['id'] == scan_id:
                    scan['status'] = 'failed'
                    scan['updated_at'] = datetime.utcnow().isoformat()
                    scan['completed_at'] = datetime.utcnow().isoformat()
                    scan['error_messages'].append(error_message)
                    scan['errors_count'] += 1
                    self._write_json(self.scans_file, data)
                    return scan
            
            return None
    
    def cancel_scan(self, scan_id: int) -> Optional[Dict]:
        """Cancel a running scan."""
        return self.update_scan(scan_id, {
            'status': 'cancelled',
            'completed_at': datetime.utcnow().isoformat(),
        })
    
    def get_scan(self, scan_id: int) -> Optional[Dict]:
        """Get scan by ID."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            for scan in data['scans']:
                if scan['id'] == scan_id:
                    return scan
        return None
    
    def get_all_scans(self, limit: int = 100, offset: int = 0, 
                      status_filter: Optional[str] = None,
                      search_query: Optional[str] = None) -> List[Dict]:
        """Get all scans with pagination and filtering."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            scans = data['scans']
            
            # Filter by status
            if status_filter:
                scans = [s for s in scans if s['status'] == status_filter]
            
            # Search query
            if search_query:
                query_lower = search_query.lower()
                scans = [
                    s for s in scans 
                    if query_lower in str(s.get('source_paths', [])) or
                       query_lower in s.get('output_dir', '').lower() or
                       query_lower in s.get('scan_mode', '').lower()
                ]
            
            # Sort by created_at descending
            scans.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Paginate
            return scans[offset:offset + limit]
    
    def delete_scan(self, scan_id: int) -> bool:
        """Delete scan and associated files."""
        with self._lock('scans'):
            # Also delete associated files
            self.delete_files_for_scan(scan_id)
            
            data = self._read_json(self.scans_file)
            original_len = len(data['scans'])
            data['scans'] = [s for s in data['scans'] if s['id'] != scan_id]
            
            if len(data['scans']) < original_len:
                self._write_json(self.scans_file, data)
                return True
            return False
    
    def get_scan_statistics(self, days: int = 30) -> Dict:
        """Get scan statistics for analytics."""
        with self._lock('scans'):
            data = self._read_json(self.scans_file)
            scans = data['scans']
            
            # Filter by date
            cutoff = datetime.utcnow()
            if days > 0:
                from datetime import timedelta
                cutoff = cutoff - timedelta(days=days)
            
            filtered = []
            for scan in scans:
                try:
                    created = datetime.fromisoformat(scan['created_at'])
                    if created >= cutoff:
                        filtered.append(scan)
                except (KeyError, ValueError):
                    continue
            
            # Calculate stats
            total = len(filtered)
            completed = sum(1 for s in filtered if s['status'] == 'completed')
            failed = sum(1 for s in filtered if s['status'] == 'failed')
            cancelled = sum(1 for s in filtered if s['status'] == 'cancelled')
            
            total_files = sum(s.get('files_scanned', 0) for s in filtered)
            total_lines = sum(s.get('lines_processed', 0) for s in filtered)
            total_bytes = sum(s.get('bytes_processed', 0) for s in filtered)
            
            # By mode
            by_mode = {}
            for scan in filtered:
                mode = scan.get('scan_mode', 'unknown')
                if mode not in by_mode:
                    by_mode[mode] = 0
                by_mode[mode] += 1
            
            return {
                'total_scans': total,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'success_rate': (completed / total * 100) if total > 0 else 0,
                'total_files_scanned': total_files,
                'total_lines_processed': total_lines,
                'total_bytes_processed': total_bytes,
                'by_mode': by_mode,
                'period_days': days,
            }
    
    # ==================== SCAN FILES ====================
    
    def add_scan_file(self, scan_id: int, file_info: Dict) -> Dict:
        """Add a file to scan tracking."""
        with self._lock('files'):
            data = self._read_json(self.files_file)
            
            file_id = self._generate_id(data)
            
            file_record = {
                'id': file_id,
                'scan_id': scan_id,
                'source_path': file_info.get('source_path', ''),
                'output_path': file_info.get('output_path', ''),
                'file_size': file_info.get('file_size', 0),
                'line_count': file_info.get('line_count', 0),
                'file_hash': file_info.get('file_hash', ''),
                'mime_type': file_info.get('mime_type', ''),
                'extension': file_info.get('extension', ''),
                'status': file_info.get('status', 'processed'),
                'error_message': file_info.get('error_message', ''),
                'processed_at': datetime.utcnow().isoformat(),
            }
            
            data['files'].append(file_record)
            self._increment_id(data)
            self._write_json(self.files_file, data)
            
            return file_record
    
    def mark_file_error(self, file_id: int, error_message: str) -> Optional[Dict]:
        """Mark a file as having an error."""
        with self._lock('files'):
            data = self._read_json(self.files_file)
            
            for file_rec in data['files']:
                if file_rec['id'] == file_id:
                    file_rec['status'] = 'error'
                    file_rec['error_message'] = error_message
                    self._write_json(self.files_file, data)
                    return file_rec
            
            return None
    
    def get_files_for_scan(self, scan_id: int, 
                           status_filter: Optional[str] = None,
                           limit: int = 1000) -> List[Dict]:
        """Get all files for a scan."""
        with self._lock('files'):
            data = self._read_json(self.files_file)
            files = [f for f in data['files'] if f['scan_id'] == scan_id]
            
            if status_filter:
                files = [f for f in files if f['status'] == status_filter]
            
            return files[:limit]
    
    def delete_files_for_scan(self, scan_id: int) -> int:
        """Delete all files associated with a scan."""
        with self._lock('files'):
            data = self._read_json(self.files_file)
            original_len = len(data['files'])
            data['files'] = [f for f in data['files'] if f['scan_id'] != scan_id]
            
            if len(data['files']) < original_len:
                self._write_json(self.files_file, data)
                return original_len - len(data['files'])
            return 0
    
    def get_file_statistics(self, scan_id: int) -> Dict:
        """Get file statistics for a scan."""
        with self._lock('files'):
            data = self._read_json(self.files_file)
            files = [f for f in data['files'] if f['scan_id'] == scan_id]
            
            total = len(files)
            processed = sum(1 for f in files if f['status'] == 'processed')
            errors = sum(1 for f in files if f['status'] == 'error')
            skipped = sum(1 for f in files if f['status'] == 'skipped')
            
            # By extension
            by_extension = {}
            for f in files:
                ext = f.get('extension', 'unknown')
                if ext not in by_extension:
                    by_extension[ext] = {'count': 0, 'size': 0}
                by_extension[ext]['count'] += 1
                by_extension[ext]['size'] += f.get('file_size', 0)
            
            total_size = sum(f.get('file_size', 0) for f in files)
            total_lines = sum(f.get('line_count', 0) for f in files)
            
            return {
                'total_files': total,
                'processed': processed,
                'errors': errors,
                'skipped': skipped,
                'total_size_bytes': total_size,
                'total_lines': total_lines,
                'by_extension': by_extension,
            }
    
    # ==================== CONFIG PROFILES ====================
    
    def save_config_profile(self, name: str, config: Dict, 
                            description: str = "",
                            is_default: bool = False) -> Dict:
        """Save a configuration profile."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            
            profile_id = self._generate_id(data)
            
            # If setting as default, unset others
            if is_default:
                for profile in data['profiles']:
                    profile['is_default'] = False
            
            profile = {
                'id': profile_id,
                'name': name,
                'config': config,
                'description': description,
                'is_default': is_default,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'usage_count': 0,
            }
            
            data['profiles'].append(profile)
            self._increment_id(data)
            self._write_json(self.configs_file, data)
            
            return profile
    
    def get_config_profile(self, profile_id: int) -> Optional[Dict]:
        """Get config profile by ID."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            for profile in data['profiles']:
                if profile['id'] == profile_id:
                    return profile
        return None
    
    def get_all_config_profiles(self) -> List[Dict]:
        """Get all config profiles."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            return data['profiles']
    
    def get_default_config_profile(self) -> Optional[Dict]:
        """Get the default config profile."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            for profile in data['profiles']:
                if profile.get('is_default', False):
                    return profile
        return None
    
    def update_config_profile(self, profile_id: int, updates: Dict) -> Optional[Dict]:
        """Update config profile."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            
            for profile in data['profiles']:
                if profile['id'] == profile_id:
                    profile.update(updates)
                    profile['updated_at'] = datetime.utcnow().isoformat()
                    
                    # Handle is_default flag
                    if updates.get('is_default', False):
                        for p in data['profiles']:
                            if p['id'] != profile_id:
                                p['is_default'] = False
                    
                    self._write_json(self.configs_file, data)
                    return profile
            
            return None
    
    def delete_config_profile(self, profile_id: int) -> bool:
        """Delete config profile."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            original_len = len(data['profiles'])
            data['profiles'] = [p for p in data['profiles'] if p['id'] != profile_id]
            
            if len(data['profiles']) < original_len:
                self._write_json(self.configs_file, data)
                return True
            return False
    
    def increment_config_usage(self, profile_id: int):
        """Increment usage count for a config profile."""
        with self._lock('configs'):
            data = self._read_json(self.configs_file)
            
            for profile in data['profiles']:
                if profile['id'] == profile_id:
                    profile['usage_count'] = profile.get('usage_count', 0) + 1
                    self._write_json(self.configs_file, data)
                    break
    
    # ==================== APP SETTINGS ====================
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting."""
        with self._lock('settings'):
            data = self._read_json(self.settings_file)
            settings = data.get('settings', {})
            return settings.get(key, default)
    
    def set_setting(self, key: str, value: Any, 
                    value_type: str = 'str',
                    category: str = 'general'):
        """Set application setting."""
        with self._lock('settings'):
            data = self._read_json(self.settings_file)
            
            data['settings'][key] = {
                'value': value,
                'type': value_type,
                'category': category,
                'updated_at': datetime.utcnow().isoformat(),
            }
            
            self._write_json(self.settings_file, data)
    
    def get_all_settings(self, category: Optional[str] = None) -> Dict:
        """Get all settings, optionally filtered by category."""
        with self._lock('settings'):
            data = self._read_json(self.settings_file)
            settings = data.get('settings', {})
            
            if category:
                return {
                    k: v for k, v in settings.items()
                    if v.get('category') == category
                }
            
            return settings
    
    def delete_setting(self, key: str) -> bool:
        """Delete a setting."""
        with self._lock('settings'):
            data = self._read_json(self.settings_file)
            
            if key in data.get('settings', {}):
                del data['settings'][key]
                self._write_json(self.settings_file, data)
                return True
            return False
    
    # ==================== INCREMENTAL CACHE ====================
    
    def get_cached_file(self, source_path: str) -> Optional[Dict]:
        """Get cached file info by source path."""
        with self._lock('cache'):
            data = self._read_json(self.cache_file)
            cache = data.get('cache', {})
            
            # Use hash of path as key for faster lookup
            path_hash = hashlib.sha256(source_path.encode()).hexdigest()[:16]
            return cache.get(path_hash)
    
    def set_cached_file(self, source_path: str, file_info: Dict):
        """Cache file info for incremental scanning."""
        with self._lock('cache'):
            data = self._read_json(self.cache_file)
            
            path_hash = hashlib.sha256(source_path.encode()).hexdigest()[:16]
            file_info['cached_at'] = datetime.utcnow().isoformat()
            file_info['source_path'] = source_path
            
            data['cache'][path_hash] = file_info
            data['last_cleanup'] = datetime.utcnow().isoformat()
            
            # Limit cache size
            if len(data['cache']) > 10000:
                # Remove oldest 20%
                items = sorted(data['cache'].items(), 
                              key=lambda x: x[1].get('cached_at', ''))
                remove_count = len(items) // 5
                for i in range(remove_count):
                    del data['cache'][items[i][0]]
            
            self._write_json(self.cache_file, data)
    
    def clear_cache(self):
        """Clear the incremental cache."""
        with self._lock('cache'):
            data = {"cache": {}, "last_cleanup": datetime.utcnow().isoformat()}
            self._write_json(self.cache_file, data)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock('cache'):
            data = self._read_json(self.cache_file)
            cache = data.get('cache', {})
            
            return {
                'cached_files': len(cache),
                'last_cleanup': data.get('last_cleanup'),
            }
