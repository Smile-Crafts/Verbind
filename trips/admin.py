from django.contrib import admin
from .models import Profile, Trip, JoinRequest, Message, Rating

admin.site.register(Profile)
admin.site.register(Trip)
admin.site.register(JoinRequest)
admin.site.register(Message)
admin.site.register(Rating)
