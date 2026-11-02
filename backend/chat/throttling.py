import time

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from rest_framework.throttling import BaseThrottle

from chat.ip import client_ip

# DRF's rate format, "10/min": the first letter of the period is what counts.
PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _count(key: str, timeout: int) -> int:
    """Adds one to a Redis counter and returns its new value, creating it at 0
    with `timeout` if it is not there. ADD (SET NX) and INCR are each atomic,
    so requests arriving together each get a different number however they
    interleave. A read, a compare and a separate write -- how DRF's throttle
    and the old daily cap counted -- let every request in flight read the same
    count and pass: 16 at once, 2 allowed, 7 to 14 got through."""
    cache.add(key, 0, timeout=timeout)
    try:
        return cache.incr(key)
    except ValueError:
        # Gone between the two calls: a per-IP key whose window just ended, or
        # Redis evicting it. Counting again starts a fresh one.
        cache.add(key, 0, timeout=timeout)
        return cache.incr(key)


def _give_back(key: str) -> None:
    """Redis DECR is atomic; one racing the key's expiry or another give-back
    cannot leave it below zero, which would grant slots past the cap."""
    try:
        if cache.decr(key) < 0:
            cache.incr(key)
    except ValueError:  # expired since it was counted: nothing to give back
        pass


class ChatRateThrottle(BaseThrottle):
    """Per-IP, in fixed windows: at most N requests per client_ip per period,
    at the rate set for the view's throttle_scope in
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] ("chat": "10/min").

    Not DRF's ScopedRateThrottle any more. That keeps each client's request
    times as a list it reads, appends to and writes back without a lock, so
    under gthread one visitor's parallel requests all read the same history
    and all passed: the limit held only for requests sent one at a time. One
    INCR per request, on a key for the current window, cannot be raced. A
    fixed window lets a burst straddle a boundary -- up to twice the rate
    across two windows -- which a courtesy limit can live with; the daily cap
    is what bounds spend.
    """

    def allow_request(self, request, view):
        scope = getattr(view, "throttle_scope", None)
        if not scope:
            return True
        # Read per call, not bound at import as DRF's THROTTLE_RATES is, so a
        # later change to REST_FRAMEWORK reaches it.
        rate = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}).get(scope)
        if not rate:
            raise ImproperlyConfigured(f"No throttle rate set for scope {scope!r}.")
        num, period = rate.split("/")
        limit, seconds = int(num), PERIODS[period[0]]

        now = time.time()
        window = int(now // seconds)
        # The scope is in the key so each view sharing this class keeps its
        # own count. A key lives one period from its first request, so it
        # outlasts its window; the index, not the expiry, is what ends one.
        count = _count(f"throttle:{scope}:{client_ip(request)}:{window}", timeout=seconds)
        # Until this window ends: DRF turns it into the 429's "Expected
        # available in N seconds." and its Retry-After header.
        self._wait = (window + 1) * seconds - now
        return count <= limit

    def wait(self):
        return self._wait


class GlobalDailyThrottle:
    """One counter for the whole service. It was sized below a free-tier daily
    quota; on a metered provider it is the daily **spend** limit instead, and
    the only thing between a scripted abuser and a real bill. Refusing here is
    cheaper than refusing upstream, and explainable to the user.

    Not a DRF throttle: ChatView.post() takes a slot itself once the body has
    validated, so only a turn that can spend counts, and answers a refusal
    with its own "daily_cap" 429. A slot is one INCR; a request whose INCR
    goes past the cap gives it straight back and is refused, so no more than
    the cap ever get through, however many arrive at once.
    """

    @staticmethod
    def take(request) -> bool:
        # The date in TIME_ZONE (Riyadh), said outright rather than left to
        # the process clock that Django happens to set from it.
        key = f"chat:daily:{timezone.localdate().isoformat()}"
        if _count(key, timeout=60 * 60 * 48) > settings.CHAT_DAILY_CAP:
            _give_back(key)
            return False
        # The key this request counted against, for refund(): recomputing it
        # later would give a turn that crossed midnight back to the wrong day.
        request.chat_daily_key = key
        return True

    @staticmethod
    def refund(request):
        """Give back the slot this request took."""
        key = getattr(request, "chat_daily_key", None)
        if key is not None:
            _give_back(key)
