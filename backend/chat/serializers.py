from rest_framework import serializers

MAX_QUESTION = 1000
MAX_HISTORY = 6


class MessageSerializer(serializers.Serializer):
    # "system" is deliberately not a choice: history is attacker-controlled and
    # is the obvious place to try to smuggle instructions into the condense prompt.
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=MAX_QUESTION, allow_blank=False,
                                     trim_whitespace=True)
    history = MessageSerializer(many=True, required=False, default=list)

    def validate_history(self, value):
        # Server-side cap regardless of what the client sends.
        return value[-MAX_HISTORY:]
