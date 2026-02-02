from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PropertyViewSet,
    BrokerViewSet,
    PropertyImageViewSet,
    PropertyFactViewSet,
    RegisterView,
    LoginView,
    GuestUserView,
    CurrentUserView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    ContactMessageView
)

router = DefaultRouter()
router.register(r'properties', PropertyViewSet)
router.register(r'brokers', BrokerViewSet)
router.register(r'property-images', PropertyImageViewSet)
router.register(r'property-facts', PropertyFactViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/guest/', GuestUserView.as_view(), name='guest'),
    path('auth/me/', CurrentUserView.as_view(), name='current_user'),

    # Custom Password Reset URLs
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('contact/', ContactMessageView.as_view(), name='contact_message'),
]
