from rest_framework.decorators import api_view
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import viewsets, status, permissions, authentication
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
import uuid
from .models import (
    Property,
    Broker,
    PropertyImage,
    PropertyFact,
    ContactMessage
)
from .serializers import (
    PropertySerializer,
    BrokerSerializer,
    PropertyImageSerializer,
    PropertyFactSerializer,
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    GuestUserSerializer,
    ContactMessageSerializer
)

class BrokerViewSet(viewsets.ModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related('broker').prefetch_related('images', 'facts').all()
    serializer_class = PropertySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 1. Area (icontains) - Search in area, municipality, or address
        area_param = self.request.query_params.get('area')
        if area_param:
            queryset = queryset.filter(
                Q(area__icontains=area_param) | 
                Q(municipality__icontains=area_param) |
                Q(address__icontains=area_param)
            )

        # 2. Rooms (min/max)
        min_rooms = self.request.query_params.get('min_rooms')
        max_rooms = self.request.query_params.get('max_rooms')
        if min_rooms:
            queryset = queryset.filter(rooms__gte=min_rooms)
        if max_rooms:
            queryset = queryset.filter(rooms__lte=max_rooms)

        # 3. Living Area / SQM (min/max)
        min_area = self.request.query_params.get('min_area')
        max_area = self.request.query_params.get('max_area')
        if min_area:
            queryset = queryset.filter(sqm__gte=min_area)
        if max_area:
            queryset = queryset.filter(sqm__lte=max_area)

        # 4. Type (exact)
        p_type = self.request.query_params.get('type')
        if p_type:
            queryset = queryset.filter(type__iexact=p_type)

        # 5. Price (min/max) - Handling string price "2 495 000 kr"
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price or max_price:
            # Since price is a string in DB (e.g. "2 500 000 kr"), we can't do direct DB comparison efficiently 
            # without complex DB functions or schema change.
            # Doing in-memory filtering for now as per plan
            
            # Helper to parse price string to int
            def parse_price(price_str):
                try:
                    # Remove 'kr' and spaces, then convert to int
                    clean_str = price_str.lower().replace('kr', '').replace(' ', '').replace(u'\xa0', '')
                    return int(clean_str)
                except (ValueError, AttributeError):
                    return 0

            # Evaluate queryset to list to filter in Python
            properties = list(queryset)
            
            if min_price:
                try:
                    min_p_val = int(min_price)
                    properties = [p for p in properties if parse_price(p.price) >= min_p_val]
                except ValueError:
                    pass
            
            if max_price:
                try:
                    max_p_val = int(max_price)
                    properties = [p for p in properties if parse_price(p.price) <= max_p_val]
                except ValueError:
                    pass

            # Return the filtered list (Note provided ID might be lost if we return list, 
            # normally we'd want to keep queryset, but for list view this is okay-ish for a prototype)
            # However, DRF expects a queryset or list.
            return properties

        return queryset

class PropertyImageViewSet(viewsets.ModelViewSet):
    queryset = PropertyImage.objects.all()
    serializer_class = PropertyImageSerializer

class PropertyFactViewSet(viewsets.ModelViewSet):
    queryset = PropertyFact.objects.all()
    serializer_class = PropertyFactSerializer


# Auth Views
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)  # Establish session after registration
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            login_input = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            # 1. Try to authenticate with username
            user = authenticate(username=login_input, password=password)
            
            # 2. If it fails, try to authenticate with email
            if user is None:
                try:
                    # Look up user by email (case-insensitive)
                    user_obj = User.objects.get(email__iexact=login_input)
                    # Authenticate using their actual username and provided password
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                login(request, user)  # Establish session cookie
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GuestUserView(APIView):
    def post(self, request):
        guest_id = str(uuid.uuid4())
        return Response({
            'message': 'Guest user created',
            'guest_id': guest_id,
            'is_guest': True
        }, status=status.HTTP_201_CREATED)


class CurrentUserView(APIView):
    # Remove strict permission here to allow ensure_csrf_cookie to work for guests too
    # We will check authentication inside the methods

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)  # Clear session cookie
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Case-insensitive email lookup
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # For security, we return success even if user not found
            return Response({'message': 'If an account exists with this email, a reset link has been sent.'}, status=status.HTTP_200_OK)
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # In production, use the actual frontend URL from settings
        reset_url = f"http://localhost:3000/reset-password/{uid}/{token}"
        
        try:
            email_subject = 'Reset your password for Daarla'
            email_message = (
                f"Hello!\n\n"
                f"We received a request to reset the password for your account on Daarla.\n\n"
                f"Please click the link below to choose a new password:\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email.\n\n"
                f"Best regards,\n"
                f"Daarla Team"
            )
            
            send_mail(
                email_subject,
                email_message,
                'noreply@daarla.se',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"ERROR: Email sending failed: {str(e)}")
            return Response({
                'error': 'Failed to send email. Please ensure your SMTP settings are correct.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': 'If an account exists with this email, a reset link has been sent.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password')
        
        print(f"DEBUG: Password Reset Attempt")
        print(f"DEBUG: UID (raw): {uidb64}")
        print(f"DEBUG: Token (raw): {token}")
        
        if not all([uidb64, token, new_password]):
            print("DEBUG: Missing required fields")
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            print(f"DEBUG: Found user: {user.username}, Last Login: {user.last_login}, Pwd Hash snippet: {user.password[:10]}")
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            print(f"DEBUG: Failed to decode UID or find user: {str(e)}")
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_valid = default_token_generator.check_token(user, token)
        print(f"DEBUG: Token validation result: {is_valid}")
        
        if not is_valid:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        print(f"DEBUG: Password reset successful for user: {user.username}")
        
        return Response({'message': 'Password has been reset successfully'}, status=status.HTTP_200_OK)

class ContactMessageView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            contact_msg = serializer.save()
            
            # Send Email Notification
            try:
                # We use your configured SMTP to notify info@daarla.se
                subject = f"New Contact Message from {contact_msg.name}"
                message = (
                    f"You have received a new message from your website contact form.\n\n"
                    f"Name: {contact_msg.name}\n"
                    f"Email: {contact_msg.email}\n"
                    f"Phone: {contact_msg.phone if contact_msg.phone else 'Not provided'}\n"
                    f"Message:\n{contact_msg.message}\n"
                )
                
                send_mail(
                    subject,
                    message,
                    'noreply@daarla.se',
                    ['pskalpana@gmail.com'], # Site admin (Testing)
                    fail_silently=False,
                )
            except Exception as e:
                print(f"ERROR: Failed to send contact email notification: {str(e)}")
                # We still return success since the message was saved in the DB
            
            return Response({
                'message': 'Your message has been sent successfully!'
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    