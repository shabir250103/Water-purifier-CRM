from django.contrib.auth import authenticate, get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied

from .serializers import (
    LoginSerializer, CreateUserSerializer, CompanySerializer
)
from .models import Company

User = get_user_model()

# ============================================================
# 🔐 AUTHENTICATION AND TOKEN MANAGEMENT
# ============================================================

class LoginView(generics.GenericAPIView):
    """
    User Login (JWT)
    - Accepts username & password
    - Returns access and refresh tokens
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {"detail": "Use POST with username and password to log in."},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"error": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
        }, status=status.HTTP_200_OK)


class AdminSigninView(generics.GenericAPIView):
    """
    Admin-only Login
    - Checks if the authenticated user is an admin or superuser
    - Returns JWT tokens
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"error": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_superuser and user.role != "admin":
            return Response(
                {"error": "Access denied. Only admins can sign in here."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Admin login successful",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
        }, status=status.HTTP_200_OK)


class AdminSignupView(generics.CreateAPIView):
    """
    Admin Signup
    - Creates the first admin/superuser account
    - Automatically marks as staff + superuser
    """
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data.copy()
        data["role"] = "admin"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(is_staff=True, is_superuser=True)

        return Response({
            "message": "Admin account created successfully!",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)


class CreateUserView(generics.CreateAPIView):
    """
    Admin creates new users
    - Only admin/superuser can access
    - Creates normal 'user' accounts
    """
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser and user.role != "admin":
            raise PermissionDenied("Only admin can create new users.")
        serializer.save(role="user", is_staff=False, is_superuser=False)


# ============================================================
# 🏢 COMPANY MANAGEMENT (Admin Only)
# ============================================================

class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for company details
    - Only admins can create or update
    - All authenticated users can read
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "admin" and not user.is_superuser:
            raise PermissionDenied("Only admin can add company details.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "admin" and not user.is_superuser:
            raise PermissionDenied("Only admin can update company details.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if getattr(user, "role", None) != "admin" and not user.is_superuser:
            raise PermissionDenied("Only admin can delete company details.")
        instance.delete()
