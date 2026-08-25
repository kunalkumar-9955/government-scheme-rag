"""
apps/users/serializers.py — User profile serializers
"""
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Full profile read/write serializer."""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    age = serializers.SerializerMethodField()
    state_display = serializers.SerializerMethodField()
    profile_completion_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserProfile
        exclude = ["user"]
        read_only_fields = ["id", "created_at", "updated_at", "profile_completion_score"]

    def get_age(self, obj):
        from datetime import date
        if obj.date_of_birth:
            today = date.today()
            return today.year - obj.date_of_birth.year - (
                (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        return None

    def get_state_display(self, obj):
        from core.utils import indian_states
        return dict(indian_states()).get(obj.state, obj.state)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial profile update serializer."""
    class Meta:
        model = UserProfile
        exclude = ["user", "id", "created_at", "updated_at", "profile_completion_score"]


class UserProfileSummarySerializer(serializers.ModelSerializer):
    """Lightweight profile for embedding in other responses."""
    class Meta:
        model = UserProfile
        fields = ["full_name", "state", "social_category", "annual_income", "occupation", "profile_completion_score"]


class EligibilityContextSerializer(serializers.Serializer):
    """Serialized context dict for RAG eligibility prompt injection."""
    def to_representation(self, instance):
        return instance.to_eligibility_context()
