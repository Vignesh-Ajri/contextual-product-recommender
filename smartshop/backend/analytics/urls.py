from django.urls import path
from .views import TrackEventView

urlpatterns = [
    path('track/', TrackEventView.as_view(), name='track_event'),
]
