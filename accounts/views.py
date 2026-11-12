from rest_framework.renderers import JSONRenderer
from django.utils import timezone
from django.conf import settings
from rest_framework.generics import CreateAPIView
from .serializers import UserSerializer
from .models import User, EmailVerificationToken, PasswordResetToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from django.contrib.sessions.models import Session
from django.contrib.auth.password_validation import validate_password
from rest_framework.generics import UpdateAPIView, RetrieveAPIView
from .serializers import ProfileSerializer
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from .mail import EmailDeliveryError, recovery_message, send_account_email, verification_message


import secrets

def verification_queryset():
    return EmailVerificationToken.objects.filter(passwordresettoken__isnull=True)

def logout_all_sessions(user):
    sessions = Session.objects.all()

    for session in sessions:
        data = session.get_decoded()

        if data.get("_auth_user_id") == str(user.pk):
            session.delete()


def frontend_link(path):
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return base + path

def send_verification_email(user, token):
    text, html = verification_message(frontend_link(f"/verify-email/{token}"))
    send_account_email(
        subject="Verify your PrepLoop email",
        recipient=user.email,
        text=text,
        html=html,
    )

def send_password_recovery_email(user, token):
    text, html = recovery_message(frontend_link(f"/reset-password/{token}"))
    send_account_email(
        subject="Reset your PrepLoop password",
        recipient=user.email,
        text=text,
        html=html,
    )

class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        token = secrets.token_urlsafe(32)

        EmailVerificationToken.objects.create(
            user=user,
            token=token
        )

        self.email_sent = True
        self.email_error = ""
        try:
            send_verification_email(user, token)
        except EmailDeliveryError as exc:
            self.email_sent = False
            self.email_error = str(exc)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        payload = dict(serializer.data)
        payload["email_sent"] = self.email_sent
        if not self.email_sent:
            payload["email_error"] = self.email_error
        return Response(payload, status=status.HTTP_201_CREATED, headers=self.get_success_headers(serializer.data))
        
class LoginView(APIView):
    
    def post(self, request):
        if request.user.is_authenticated:
            return Response({
                    "detail": "You are already Login"
            })
             
        username = request.data.get("username")
        password = request.data.get("password")
        
        user = authenticate(
            request,
            username=username,
            password=password,
        )
        
        if user is None:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request, user)

        return Response({
            "detail": "Login successful"
        })
        
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)  
        return Response({"message": "You are logout"}, status=status.HTTP_200_OK)
        
class EditProfileView(UpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
class CurrentUserView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})
        

class EmailVerificationView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request, token):
        verification_token = verification_queryset().filter(token=token).first()

        current_time = timezone.now()

        if verification_token is None:
            return Response(
                {"message": "Invalid Token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification_token.user.account_status == User.AccountStatus.ACTIVE:
            return Response(
                {"message": "Your Email has already been verified"}
            )

        if verification_token.expires_at > current_time:
            verification_token.user.account_status = User.AccountStatus.ACTIVE
            verification_token.user.save(update_fields=["account_status"])
            verification_token.delete()

            return Response(
                {"message": "Your Email has been verified"}
            )
        
        
        verification_token.delete()
        return Response(
            {"message": "Your Token has expired"},
            status=status.HTTP_410_GONE
        )

class ResendVerificationEmail(APIView):
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]  

    def post(self, request):
        user = request.user

        if user.account_status == User.AccountStatus.ACTIVE:
            return Response({"message": "Your email is already verified"})

        verification_queryset().filter(user=user).delete()

        token = secrets.token_urlsafe(32)
        EmailVerificationToken.objects.create(user=user, token=token)

        try:
            send_verification_email(user, token)
        except EmailDeliveryError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"message": "Verification email sent"})

class PasswordRecoveryLink(APIView):
    renderer_classes = [JSONRenderer]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")

        user = User.objects.filter(
            username=username,
            email=email
        ).first()

        if user is None:
            return Response(
                {
                    "message":
                    "If an account with these details exists, "
                    "a password reset link has been sent to your email"
                }
            )

        if user.account_status == User.AccountStatus.PENDING_VERIFICATION:
            return Response(
                {"message": "Your email isn't verified"},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.account_status == User.AccountStatus.SUSPENDED:
            return Response(
                {"message": "Your account has been suspended"},
                status=status.HTTP_403_FORBIDDEN
            )

        PasswordResetToken.objects.filter(user=user).delete()
        token = secrets.token_urlsafe(32)

        PasswordResetToken.objects.create(
            user=user,
            token=token
        )

        try:
            send_password_recovery_email(user, token)
        except EmailDeliveryError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            {
                "message":
                "A password reset link has been sent to your email"
            }
        )

class PasswordResetView(APIView):
    def get_renderers(self):
        if self.request.method == "POST":
            return [JSONRenderer()]

        return super().get_renderers()

    def post(self, request, token):
        password = request.data.get("password")

        if password is None:
            return Response(
                {"message": "Please give a password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_column = PasswordResetToken.objects.filter(
            token=token
        ).first()

        current_time = timezone.now()

        if token_column is None:
            return Response(
                {"message": "Invalid Password Resetting Link"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if token_column.expires_at <= current_time:
            return Response(
                {"message": "Your Password Reset Link has expired"},
                status=status.HTTP_410_GONE
            )

        user = token_column.user
        try:
            validate_password(password, user=user)

        except ValidationError as e:
            return Response(
                {"message": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(password)

        user.save(update_fields=["password"])

        token_column.delete()

        logout_all_sessions(user)

        return Response(
            {"message": "Your Password has successfully changed"}
        )



class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response(
                {"message": "Please provide your current and new password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        if not check_password(current_password, user.password):
            return Response(
                {"message": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user=user)

        except ValidationError as e:
            return Response(
                {"message": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        
        return Response(
            {"message": "Your password has successfully changed"}
        )
        
class DeleteProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        if user.username != username:
            return Response(
                {"detail": "Username is not correct"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logout(request)
        user.delete()

        return Response(
            {"detail": "Account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
