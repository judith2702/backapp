from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Broker,
    Property,
    PropertyImage,
    PropertyFact,
    Profile,
    ContactMessage
)

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'phone', 'message', 'created_at']

class BrokerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broker
        fields = ['id','name', 'image_url', 'phone', 'email']

class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = [
            'id',
            'image_url',
        ]

class PropertyFactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFact
        fields = [
            'id',
            'label',
            'value',
        ]

class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    facts = PropertyFactSerializer(many=True, read_only=True)
    broker = BrokerSerializer(read_only=True)
    class Meta:
        model = Property
        fields = [
            'id',
            'type',
            'address',
            'area',
            'municipality',
            'price',
            'sqm',
            'rooms',
            'fee',
            'published',
            'is_bidding',
            'renovation_level',
            'description',
            'created_at',
            'broker',
            'images',
            'facts',
        ]

# Auth Serializers
class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number']
        read_only_fields = ['username']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            representation['phone_number'] = instance.profile.phone_number
        except (Profile.DoesNotExist, AttributeError):
            representation['phone_number'] = ""
        return representation

    def update(self, instance, validated_data):
        phone_number = validated_data.pop('phone_number', None)

        instance = super().update(instance, validated_data)

        # Update profile phone number
        profile, created = Profile.objects.get_or_create(user=instance)
        if phone_number is not None:
            profile.phone_number = phone_number
            profile.save()
            print(f"DEBUG: Profile saved - phone_number: {profile.phone_number}")

        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Normalize email to lowercase
        if 'email' in data:
            data['email'] = data['email'].lower()
            
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        
        # Profile is created via signal automatically
        
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class GuestUserSerializer(serializers.Serializer):
    guest_id = serializers.CharField()
    is_guest = serializers.BooleanField()
