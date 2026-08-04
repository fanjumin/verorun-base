#!/usr/bin/env python3
"""
Vault Storage Adapter — Abstract base class for all storage backends.

All storage backends (S3/OSS/Azure/GCS/SFTP/WebDAV) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional
import json


class BaseStorageAdapter(ABC):
    """Storage adapter base class."""

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get('name', 'unnamed')

    @abstractmethod
    def upload(self, file_path: str, object_name: str) -> bool:
        """Upload file to remote storage."""
        pass

    @abstractmethod
    def download(self, object_name: str, file_path: str) -> bool:
        """Download file from remote storage."""
        pass

    @abstractmethod
    def delete(self, object_name: str) -> bool:
        """Delete file from remote storage."""
        pass

    @abstractmethod
    def list_objects(self, prefix: str = '') -> list:
        """List objects in remote storage."""
        pass

    @abstractmethod
    def test_connection(self) -> dict:
        """Test connection health. Returns {'ok': bool, 'error': str|None}."""
        pass

    def get_size(self, object_name: str) -> Optional[int]:
        """Get object size in bytes. Optional."""
        return None


class StorageRouter:
    """Multi-target storage router supporting 3-2-1 backup strategy."""

    def __init__(self):
        self._adapters = {}
        self._load_adapters()

    def _load_adapters(self):
        """Load all enabled storage targets from database."""
        try:
            from plugins._base.db import get_raw_connection
            conn = get_raw_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, storage_type, config
                FROM vault_storage_targets
                WHERE enabled = TRUE
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()

            for row in rows:
                target_id, name, stype, config = row
                if isinstance(config, str):
                    config = json.loads(config)
                config['name'] = name
                adapter = self._create_adapter(stype, config)
                if adapter:
                    self._adapters[target_id] = adapter
        except Exception as e:
            print(f'[Vault] Failed to load storage adapters: {e}')

    def _create_adapter(self, storage_type: str, config: dict) -> BaseStorageAdapter:
        """Factory: create adapter instance by storage type. Returns None if not available."""
        if storage_type == 's3':
            try:
                from .s3 import S3Adapter
                return S3Adapter(config)
            except ImportError:
                print('[Vault] S3 adapter not available (boto3 required)')
        elif storage_type == 'oss':
            try:
                from .oss import OSSAdapter
                return OSSAdapter(config)
            except ImportError:
                print('[Vault] OSS adapter not available (oss2 required)')
        elif storage_type == 'sftp':
            try:
                from .sftp import SFTPAdapter
                return SFTPAdapter(config)
            except ImportError:
                print('[Vault] SFTP adapter not available (paramiko required)')
        elif storage_type == 'local':
            try:
                from .local import LocalAdapter
                return LocalAdapter(config)
            except ImportError:
                print('[Vault] Local adapter not available')
        else:
            print(f'[Vault] Unknown storage type: {storage_type}')
        return None

    def upload_to_all(self, file_path: str, object_name: str) -> list:
        """Upload to all enabled storage targets."""
        results = []
        for target_id, adapter in self._adapters.items():
            try:
                ok = adapter.upload(file_path, object_name)
                results.append({
                    'target_id': target_id,
                    'target_name': adapter.name,
                    'uploaded': ok,
                    'error': None if ok else 'Upload failed',
                })
            except Exception as e:
                results.append({
                    'target_id': target_id,
                    'target_name': adapter.name,
                    'uploaded': False,
                    'error': str(e),
                })
        return results

    def test_all(self) -> dict:
        """Test connectivity for all storage targets."""
        results = {}
        for target_id, adapter in self._adapters.items():
            results[target_id] = adapter.test_connection()
        return results
