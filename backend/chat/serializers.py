from rest_framework import serializers

MAX_QUESTION = 1000
MAX_HISTORY = 6
MAX_HISTORY_CONTENT = 2000


class MessageSerializer(serializers.Serializer):
    # "system" is deliberately not a choice: history is attacker-controlled and
    # is the obvious place to try to smuggle instructions into the condense prompt.
    role = serializers.ChoiceField(choices=["user", "assistant"])
    # Blank allowed and long truncated, not rejected: the browser echoes the
    # bot's own answers back as history, and one odd answer must not turn
    # every later question in that conversation into a 400. The cap still
    # bounds what reaches the condense prompt.
    content = serializers.CharField(allow_blank=True, trim_whitespace=True)

    def validate_content(self, value):
        return value[:MAX_HISTORY_CONTENT]


class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=MAX_QUESTION, allow_blank=False,
                                     trim_whitespace=True)
    history = MessageSerializer(many=True, required=False, default=list)

    def validate_history(self, value):
        # Server-side cap regardless of what the client sends.
        return value[-MAX_HISTORY:]
