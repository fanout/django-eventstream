from django.urls import path, include
import django_eventstream
from . import views

urlpatterns = [
    path('', views.home),
    path('events/', include(django_eventstream.urls), {
        'channels': ['time']
    }),
]
