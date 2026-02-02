from django.contrib import admin
from .models import Property, Broker, PropertyImage, PropertyFact, Profile, ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
    list_filter = ('created_at',)

admin.site.register(Property)
admin.site.register(Broker)
admin.site.register(PropertyImage)
admin.site.register(PropertyFact)
admin.site.register(Profile)
