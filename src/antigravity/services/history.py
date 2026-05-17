"""
Scan History Service - Manages scan records, analytics, and config profiles using JSON storage.
Wrapper around JSONStore for backward compatibility.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from antigravity.services.json_store import JSONStore


class ScanHistoryService:
    """Service for managing scan history, analytics, and configuration profiles using JSON files."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the scan history service.
        
        Args:
            data_dir: Directory to store JSON files. Defaults to ./data
        """
        if data_dir is None:
            import os
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        
        self.store = JSONStore(data_dir=data_dir)
    
    # ========== Scan Record Management ==========
    
    def create_record(
        self,
        root_path: str,
        output_path: Optional[str] = None,
        scan_mode: str = "single",
        config_json: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new scan record and return its ID."""
        config = {
            "root_path": root_path,
            "output_path": output_path,
            "scan_mode": scan_mode,
            "config_json": config_json or {},
        }
        scan = self.store.create_scan(config)
        return scan["id"]
    
    def update_record(
        self,
        record_id: int,
        files_scanned: Optional[int] = None,
        files_processed: Optional[int] = None,
        files_skipped: Optional[int] = None,
        bytes_processed: Optional[int] = None,
        lines_processed: Optional[int] = None,
        errors_count: Optional[int] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update an existing scan record with progress data."""
        updates = {}
        if files_scanned is not None:
            updates["files_scanned"] = files_scanned
        if files_processed is not None:
            updates["files_processed"] = files_processed
        if files_skipped is not None:
            updates["files_skipped"] = files_skipped
        if bytes_processed is not None:
            updates["bytes_processed"] = bytes_processed
        if lines_processed is not None:
            updates["lines_processed"] = lines_processed
        if errors_count is not None:
            updates["errors_count"] = errors_count
        if status is not None:
            updates["status"] = status
        if error_message is not None:
            updates["error_message"] = error_message
        
        if updates:
            self.store.update_scan(record_id, updates)
    
    def complete_record(self, record_id: int, summary: Dict[str, Any]) -> None:
        """Mark a scan record as completed with final metrics."""
        self.store.complete_scan(record_id, summary)
    
    def fail_record(self, record_id: int, error_message: str) -> None:
        """Mark a scan record as failed."""
        self.store.fail_scan(record_id, error_message)
    
    def cancel_record(self, record_id: int) -> None:
        """Mark a scan record as cancelled."""
        self.store.cancel_scan(record_id)
    
    def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        scan_mode_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all scan records with pagination and filters."""
        return self.store.get_all_scans(limit=limit, offset=offset, status_filter=status_filter, scan_mode_filter=scan_mode_filter)
    
    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Get a single scan record by ID."""
        return self.store.get_scan(record_id)
    
    def delete_record(self, record_id: int) -> bool:
        """Delete a scan record and its associated files."""
        return self.store.delete_scan(record_id)
    
    # ========== File-Level Tracking ==========
    
    def add_file_to_scan(
        self,
        scan_record_id: int,
        relative_path: str,
        absolute_path: str,
        extension: str,
        size_bytes: int = 0,
        lines_count: int = 0,
        encoding: Optional[str] = None,
        mime_type: Optional[str] = None,
        file_hash: Optional[str] = None,
    ) -> int:
        """Add a file to a scan record."""
        file_info = {
            "relative_path": relative_path,
            "absolute_path": absolute_path,
            "extension": extension,
            "size_bytes": size_bytes,
            "lines_count": lines_count,
            "encoding": encoding,
            "mime_type": mime_type,
            "file_hash": file_hash,
        }
        result = self.store.add_scan_file(scan_record_id, file_info)
        return result["id"]
    
    def mark_file_processed(
        self,
        file_id: int,
        output_file: Optional[str] = None,
        chunk_index: Optional[int] = None,
    ) -> None:
        """Mark a file as processed."""
        # Note: JSONStore doesn't have this exact method, would need to be added
        pass
    
    def mark_file_skipped(
        self,
        file_id: int,
        skip_reason: str,
    ) -> None:
        """Mark a file as skipped."""
        pass
    
    def mark_file_error(
        self,
        file_id: int,
        error_message: str,
    ) -> None:
        """Mark a file with an error."""
        self.store.mark_file_error(file_id, error_message)
    
    def get_files_for_scan(
        self,
        scan_record_id: int,
        processed_only: bool = False,
        skipped_only: bool = False,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get files for a specific scan record."""
        return self.store.get_files_for_scan(scan_record_id, limit=limit)
    
    def delete_files_for_scan(self, scan_record_id: int) -> None:
        """Delete all files associated with a scan record."""
        self.store.delete_files_for_scan(scan_record_id)
    
    # ========== Analytics ==========
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for scans in the last N days."""
        return self.store.get_scan_statistics(days=days)
    
    # ========== Config Profile Management ==========
    
    def save_config_profile(
        self,
        name: str,
        config_json: Dict[str, Any],
        description: Optional[str] = None,
        is_default: bool = False,
    ) -> int:
        """Save a configuration profile."""
        profile = self.store.save_config_profile(name, config_json, description or "", is_default)
        return profile["id"]
    
    def get_config_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a configuration profile by name."""
        return self.store.get_config_profile(name)
    
    def get_all_config_profiles(self) -> List[Dict[str, Any]]:
        """Get all configuration profiles."""
        return self.store.get_all_config_profiles()
    
    def delete_config_profile(self, name: str) -> bool:
        """Delete a configuration profile (cannot delete system profiles)."""
        return self.store.delete_config_profile(name)
    
    def get_default_config_profile(self) -> Optional[Dict[str, Any]]:
        """Get the default configuration profile."""
        return self.store.get_default_config_profile()
    
    # ========== App Settings ==========
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an application setting."""
        result = self.store.get_setting(key)
        return result if result is not None else default
    
    def set_setting(
        self,
        key: str,
        value: Any,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_public: bool = True,
        is_editable: bool = True,
    ) -> None:
        """Set an application setting."""
        self.store.set_setting(key, value, description or "", category or "general")
    
    def get_all_settings(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all application settings, optionally filtered by category."""
        return self.store.get_all_settings(category=category)
