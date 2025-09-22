"""A lightweight, in-memory dummy replacement for az_intf.api used by tests.

This module implements the small az_api surface the application uses so tests
can replace the real `az_intf.api` entrypoints with these functions without
modifying application code.

Functions provided:
 - init_container(user, username, assign, email) -> bool
 - get_container_instance(username) -> DummyContainer | None
 - del_container_instance(username) -> bool

And a `DummyContainer` class with the methods used by views:
 - blob_create(name, size, typ, uploaded=None) -> (bool, blob_id)
 - blob_delete(blob_id) -> bool
 - get_blob_list() -> list
 - container_delete(user_obj) -> bool
"""

from typing import Dict, Tuple, Optional

_instances: Dict[str, "DummyContainer"] = {}


class DummyContainer:
    def __init__(self, create_result: Tuple[bool, Optional[str]] = (True, "blob-12345")):
        self._create_result = create_result

    def blob_create(self, name, size, typ, uploaded=None):
        # ignore uploaded file; return configured result
        return self._create_result

    def blob_delete(self, blob_id):
        return True

    def get_blob_list(self):
        # return empty list compatible with views
        return []

    def container_delete(self, user_obj):
        return True

    def recalculate_storage_usage(self):
        # Dummy implementation for testing
        return True

    def get_blob_info(self):
        # Dummy implementation for testing - return empty list
        return []

    def validate_new_blob_addition(self, file_size, file_name):
        # Dummy implementation for testing - always allow uploads
        return (True, "Upload allowed")

    def initialize_streaming_upload(self, file_name, upload_id, total_size):
        """Dummy implementation for streaming upload initialization"""
        return {'success': True, 'blob_id': f'blob-{upload_id[:8]}'}

    def append_chunk_to_blob(self, upload_id, chunk_data, chunk_index):
        """Dummy implementation for chunk appending"""
        return {'success': True, 'uploaded_size': chunk_data.size}

    def finalize_streaming_upload(self, upload_id, file_name):
        """Dummy implementation for streaming upload finalization"""
        return {
            'success': True, 
            'blob_id': f'blob-final-{upload_id[:8]}',
            'uploaded_size': 1024,
            'duration': 0.5
        }

    def initialize_streaming_upload(self, file_name, upload_id, total_size):
        # Dummy implementation for streaming upload testing
        return {'success': True, 'blob_id': 'dummy-blob-123'}

    def append_chunk_to_blob(self, upload_id, chunk_data, chunk_index):
        # Dummy implementation - simulate successful chunk append
        return {'success': True}

    def finalize_streaming_upload(self, upload_id, file_name):
        # Dummy implementation - simulate successful finalization
        return {'success': True, 'blob_id': 'dummy-blob-123'}


def init_container(user, username, assign, email) -> bool:
    # Create and register a dummy container instance for username
    _instances[username] = DummyContainer()
    return True


def get_container_instance(username) -> Optional[DummyContainer]:
    # Lazily create a DummyContainer to mirror behavior of init_container
    if username not in _instances:
        _instances[username] = DummyContainer()
    return _instances.get(username)


def del_container_instance(username) -> bool:
    _instances.pop(username, None)
    return True
