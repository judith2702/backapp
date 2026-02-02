from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.

# Broker Model #
class Broker(models.Model):
    name = models.CharField(max_length=100)
    image_url = models.URLField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.name

# Property Model #
class Property(models.Model):
    PROPERTY_TYPES = [
        ('Villa', 'Villa'),
        ('Apartment', 'Apartment'),
        ('House', 'House'),
    ]

    type = models.CharField(max_length=50, choices=PROPERTY_TYPES)
    address = models.CharField(max_length=255)
    area = models.CharField(max_length=100)
    municipality = models.CharField(max_length=100)

    price = models.CharField(max_length=50)  # "24 900 000 kr"
    sqm = models.PositiveIntegerField()
    rooms = models.PositiveIntegerField()

    fee = models.CharField(max_length=50, blank=True, null=True)

    published = models.CharField(max_length=50)  # "Yesterday"
    is_bidding = models.BooleanField(default=False)

    RENOVATION_LEVELS = [
        ('none', 'None'),
        ('basic', 'Basic'),
        ('plus', 'Plus'),
        ('premium', 'Premium'),
    ]
    renovation_level = models.CharField(
        max_length=20,
        choices=RENOVATION_LEVELS,
        default='none'
    )

    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    broker = models.ForeignKey(
        Broker,
        related_name='properties',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.type} - {self.address}"

# Property Images (Multiple images) #
class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        related_name='images',
        on_delete=models.CASCADE
    )
    image_url = models.URLField()

    def __str__(self):
        return f"Image for {self.property.address}"

# Property Facts (Label / Value) #

class PropertyFact(models.Model):
    property = models.ForeignKey(
        Property,
        related_name='facts',
        on_delete=models.CASCADE
    )
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.label}: {self.value}"


# User Profile Model #
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

# Signals to handle Profile creation/updates #
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.get_or_create(user=instance)
    instance.profile.save()

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

