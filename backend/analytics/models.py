from django.db import models


class PageView(models.Model):
    """One page load by a browser that ran the beacon.

    Holds no raw IP and no User-Agent string: `ip_hash` is chat.models.hash_ip,
    the same key ChatLog uses, so "visitors who used the chat" is a join, and
    the UA is reduced to coarse families before it is saved.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_hash = models.CharField(max_length=64, db_index=True)
    path = models.CharField(max_length=200)
    referrer_host = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, blank=True)
    device = models.CharField(max_length=10)
    browser = models.CharField(max_length=20)

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.path}"
