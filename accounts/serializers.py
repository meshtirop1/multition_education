from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'status',
                  'email_verified', 'bio', 'profile_picture', 'date_joined']
        read_only_fields = ['id', 'date_joined', 'role', 'status', 'email_verified']


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'email', 'status', 'date_joined', 'email_verified']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected', 'suspended'])
