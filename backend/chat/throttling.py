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
    """One counter for the whole service. It was sized below a free-tier daily
    quota; on a metered provider it is the daily **spend** limit instead, and
    the only thing between a scripted abuser and a real bill. Refusing here is
    cheaper than refusing upstream, and explainable to the user.

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
        # The key this request counted against, for refund(): recomputing it
        # later would give a turn that crossed midnight back to the wrong day.
        request.chat_daily_key = key
        return True

    def wait(self):
        return None

    @staticmethod
    def refund(request):
        """Give back the slot this request counted. Redis DECR is atomic; a
        refund racing the key's expiry or another refund cannot leave it below
        zero, which would grant slots past the cap."""
        key = getattr(request, "chat_daily_key", None)
        if key is None:
            return
        try:
            if cache.decr(key) < 0:
                cache.incr(key)
        except ValueError:  # expired since it was counted: nothing to give back
            pass
