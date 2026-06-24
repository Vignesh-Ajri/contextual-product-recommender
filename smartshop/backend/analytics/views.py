import requests
import logging
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from .models import UserEvent
from .serializers import UserEventSerializer
import threading

logger = logging.getLogger(__name__)

def forward_to_cprp(event_data, user_email=""):
    """Forward the event to the existing CPRP Flask API in a background thread."""
    
    cprp_payload = {
        "user_id": event_data.get('user') or event_data.get('user_id') or event_data.get('session_id') or 'anonymous',
        "event_type": event_data.get('event_type') or 'view',
        "category": event_data.get('cprp_category') or 'unknown',
        "brand": event_data.get('cprp_brand') or 'unknown',
        "price_range": event_data.get('cprp_price_range') or 'unknown',
        "product_name": event_data.get('cprp_product_name') or '',
        "search_query": event_data.get('search_query') or '',
        "session_id": event_data.get('session_id') or 'anon',
        "device_type": event_data.get('device_type') or 'desktop',
        "platform": event_data.get('platform') or 'web',
        "email": user_email,
    }

    url = f"{settings.CPRP_API_URL}/event"
    try:
        # Assuming CPRP allows unauthenticated events or we need a service token. 
        # Using a timeout to not block the thread indefinitely
        response = requests.post(url, json=cprp_payload, timeout=5)
        if response.status_code in [200, 201]:
            logger.info("Successfully forwarded event to CPRP.")
        else:
            logger.warning(f"Failed to forward event to CPRP: {response.text}")
    except Exception as e:
        logger.error(f"Error forwarding event to CPRP: {e}")

from rest_framework.permissions import AllowAny

class TrackEventView(generics.CreateAPIView):
    serializer_class = UserEventSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user_email = ""
        
        if request.user.is_authenticated:
            data['user'] = request.user.id
            user_email = request.user.email
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Async forward to CPRP
        threading.Thread(target=forward_to_cprp, args=(serializer.data, user_email)).start()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
