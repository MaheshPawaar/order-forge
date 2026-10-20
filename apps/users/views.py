from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.users.serializers import RegistrationSerializer


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
