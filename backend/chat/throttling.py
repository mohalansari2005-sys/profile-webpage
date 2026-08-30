from datetime import date

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle

from chat.ip import client_ip


class ChatRateThrottle(ScopedRateThrottle):
    """Per-IP. Rate from REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['chat']."""

    def get_ident(self, request):
        return client_ip(request)

    def get_rate(self):
        # DRF binds SimpleRateThrottle.THROTTLE_RATES as a class attribute at
        # import time, so a later change to REST_FRAMEWORK never reaches it.
        # Reading settings per call keeps the configured rate authoritative.
        rates = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope) or super().get_rate()


class GlobalDailyThrottle(BaseThrottle):
    """One counter for the whole service, sized below the Gemini free-tier
    daily quota so the system refuses politely instead of collapsing into
    upstream quota errors it cannot explain to the user.

    Extends BaseThrottle, not ScopedRateThrottle: it replaces allow_request
    wholesale and never consults a rate string, so inheriting the sliding
    window machinery would only mislead.
    """

    def allow_request(self, request, view):
        cap = settings.CHAT_DAILY_CAP
        key = f"chat:daily:{date.today().isoformat()}"
        used = cache.get_or_set(key, 0, timeout=60 * 60 * 48)
        if used >= cap:
            return False
        try:
            cache.incr(key)
        except ValueError:  # key expired between get_or_set and incr
            cache.set(key, 1, timeout=60 * 60 * 48)
        return True

    def wait(self):
        return None
