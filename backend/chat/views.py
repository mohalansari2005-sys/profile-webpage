import time

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.graph.build import build_graph
from chat.ip import client_ip
from chat.models import hash_ip
from chat.openai_client import turn_budget
from chat.origin import live_site
from chat.serializers import ChatRequestSerializer
from chat.throttling import ChatRateThrottle, GlobalDailyThrottle

# Compiled once at import: compilation is pure wiring, and repeating it per
# request would add latency for nothing.
GRAPH = build_graph()


def synthetic(request) -> bool:
    """True for a question that did not come from the live site: the daily
    canary and curl checks send no Origin, a Vercel preview sends its own. Only
    CORS_ALLOWED_ORIGINS count as real (chat/origin.py), not the *.vercel.app
    pattern CORS also lets through. The turn is answered as usual; the
    dashboard just leaves it out of the numbers."""
    return not live_site(request.META.get("HTTP_ORIGIN", ""))


class ChatView(APIView):
    # Anonymous by design. DRF's defaults (session + Basic) authenticate before
    # any throttle runs, and Basic runs a million-round password hash for every
    # request carrying the header -- uncounted work anyone could ask for.
    authentication_classes = []
    permission_classes = []
    throttle_scope = "chat"
    # Per-IP only. GlobalDailyThrottle counts as it asks, so post() asks it
    # last: a request this limit turns away never reaches it, and neither does
    # one whose body fails validation.
    throttle_classes = [ChatRateThrottle]

    def check_throttles(self, request):
        # Only a POST can become a chat turn. Anything else is a 405 (or
        # OPTIONS' metadata) that costs nothing, and must not spend the
        # visitor's per-IP budget. CORS preflights never get here: corsheaders
        # answers them.
        if request.method == "POST":
            super().check_throttles(request)

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # The daily cap is the spend limit, so only a turn that can spend may
        # count. Checked in DRF's throttle pass, every GET, HEAD, OPTIONS and
        # 400 counted too: a scanner or an uptime check could close the chat
        # for the day without a cent spent.
        if not GlobalDailyThrottle.take(request):
            # Its own code: a per-IP 429 clears in a minute, this one at
            # midnight, and the UI can only tell visitors which if it is told.
            return Response({"detail": "Today's question limit has been reached. "
                                       "Please try again tomorrow.",
                             "code": "daily_cap"},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        with turn_budget(settings.CHAT_TURN_BUDGET):
            result = GRAPH.invoke({
                "question": data["question"],
                "history": [dict(m) for m in data["history"]],
                "ip_hash": hash_ip(client_ip(request)),
                "started_at": time.monotonic(),
                "synthetic": synthetic(request),
            })

        if result.get("unavailable"):
            # OpenAI failed, not the question. Answering with a refusal told
            # every visitor their question was off-topic for ten days after
            # gpt-4.1-nano was retired; a 503 makes the UI say the service hit
            # an error and offer a retry. The turn is already in ChatLog.
            if not result.get("in_scope"):
                # It never got past the gate, so at most a classifier call was
                # billed: give the slot back, or retries during a quota outage
                # would leave the cap spent when OpenAI recovers. A turn that
                # reached retrieval or generate keeps counting -- refunding
                # those let a partial outage spend without limit.
                GlobalDailyThrottle.refund(request)
            return Response({"detail": "The answer service is temporarily unavailable."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            {"answer": result.get("answer", ""),
             "sources": result.get("sources", []),
             "refused": bool(result.get("refused", True))},
            status=status.HTTP_200_OK,
        )
