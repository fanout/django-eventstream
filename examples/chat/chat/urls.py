from django.urls import path, include
import django_eventstream
from . import views

urlpatterns = [
	path('', views.home),
	path('<room_id>', views.home),
	path('rooms/<room_id>/messages/', views.messages),
	path('rooms/<room_id>/events/', include(django_eventstream.urls), {'format-channels': ['room-{room_id}']}),

	# older endpoint allowing client to select channel. not recommended
	path('/events/', include(django_eventstream.urls)),
]
