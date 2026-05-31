from rest_framework import serializers
from .models import UserEvent

class UserEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvent
        fields = '__all__'
        read_only_fields = ('synced_to_cprp',)
