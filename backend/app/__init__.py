"""
@file: __init__.py
@description: Makes 'app' a Python package.
@dependencies: None
@created: [v1] 2025-05-18
""" 

from .redis_utils import get_redis_connection

__all__ = ["get_redis_connection"] 