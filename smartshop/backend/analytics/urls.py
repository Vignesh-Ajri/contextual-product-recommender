from django.urls import path
from .views import TrackEventView, RecentEventsView

urlpatterns = [
    path('track/', TrackEventView.as_view(), name='track_event'),
    path('events/', RecentEventsView.as_view(), name='recent_events'),
]
