from rest_framework import serializers
from django.contrib.auth import get_user_model
from google.auth.transport import requests
from google.oauth2 import id_token
from django.conf import settings

User = get_user_model()

class GoogleAuthSerializer(serializers.Serializer):
    token = serializers.CharField()
    
    def validate_token(self, value):
        try:
            # Verificar token do Google
            idinfo = id_token.verify_oauth2_token(
                value, requests.Request(), settings.GOOGLE_CLIENT_ID)
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise serializers.ValidationError('Token inválido')
            
            return idinfo
        except ValueError:
            raise serializers.ValidationError('Token inválido')

class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar_url', 'cargo', 'groups']