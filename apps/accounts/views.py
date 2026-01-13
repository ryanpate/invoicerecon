from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Firm
from .serializers import UserSerializer, FirmSerializer


class CurrentUserView(APIView):
    """Get current authenticated user."""

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class FirmDetailView(LoginRequiredMixin, APIView):
    """Get current user's firm details."""

    def get(self, request):
        if not request.user.firm:
            return Response(
                {'error': 'No firm associated with this account'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = FirmSerializer(request.user.firm)
        return Response(serializer.data)
