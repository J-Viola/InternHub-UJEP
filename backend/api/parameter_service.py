import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)
CACHE_PREFIX = "system_parameter:"


def _valid(value, default):
    if isinstance(default, int) and not isinstance(default, bool):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, list) and all(isinstance(item, int) and not isinstance(item, bool) for item in default):
        return isinstance(value, list) and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return type(value) is type(default)


def get_param(key, default):
    """Return a typed administrator override, falling back to Django settings."""
    fallback = getattr(settings, key, default)
    cache_key = CACHE_PREFIX + key
    cached = cache.get(cache_key, ...)
    if cached is not ...:
        return cached
    try:
        from api.models import SystemParameter

        parameter = SystemParameter.objects.filter(key=key).first()
    except Exception:
        # Keep settings-based behavior available during migrations/startup or DB outages.
        logger.warning("Nepodařilo se načíst systémový parametr %s; používá se výchozí hodnota.", key, exc_info=True)
        return fallback
    value = fallback
    if parameter is not None:
        if _valid(parameter.value, fallback):
            value = parameter.value
        else:
            logger.warning("Neplatná hodnota systémového parametru %s; používá se hodnota z settings.", key)
    cache.set(cache_key, value, timeout=None)
    return value


def invalidate_param_cache(key):
    cache.delete(CACHE_PREFIX + key)
