"""Limiter global compartilhado entre app.py e routers.

Em testes, importe e setar `limiter.enabled = False` no conftest.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
