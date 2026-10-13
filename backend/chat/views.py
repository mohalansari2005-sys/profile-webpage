import time

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.graph.build import build_graph
from chat.ip import client_ip
from chat.models import hash_ip
from chat.serializers import ChatRequestSerializer
from chat.throttling import ChatRateThrottle, GlobalDailyThrottle

# Compiled once at import: compilation is pure wiring, and repeating it per
# request would add latency for nothing.
GRAPH = build_graph()


class ChatView(APIView):
    throttle_scope = "chat"
    # Per-IP first, and the first refusal ends the check (below), so a request
    # the per-IP limit turns away never counts against the global cap.
    throttle_classes = [ChatRateThrottle, GlobalDailyThrottle]

    def check_throttles(self, request):
        # DRF's own version asks every throttle even after one refuses, and
        # GlobalDailyThrottle counts as it asks. One client spamming past its
        # per-IP limit would then burn the whole day's cap for every visitor.
        for throttle in self.get_throttles():
            if not throttle.allow_request(request, self):
                self.throttled(request, throttle.wait())

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = GRAPH.invoke({
            "question": data["question"],
            "history": [dict(m) for m in data["history"]],
            "ip_hash": hash_ip(client_ip(request)),
            "started_at": time.monotonic(),
        })

        return Response(
            {"answer": result.get("answer", ""),
             "sources": result.get("sources", []),
             "refused": bool(result.get("refused", True))},
            status=status.HTTP_200_OK,
        )
