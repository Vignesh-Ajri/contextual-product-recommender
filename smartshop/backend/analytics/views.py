import requests
import logging
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from .models import UserEvent
from .serializers import UserEventSerializer
import threading

logger = logging.getLogger(__name__)

def forward_to_cprp(event_data):
    """Forward the event to the existing CPRP Flask API in a background thread."""
    
    cprp_payload = {
        "user_id": event_data.get('user_id') or event_data.get('session_id'),
        "event_type": event_data.get('event_type'),
        "category": event_data.get('cprp_category', 'unknown'),
        "brand": event_data.get('cprp_brand', 'unknown'),
        "price_range": event_data.get('cprp_price_range', 'unknown'),
        "product_name": event_data.get('cprp_product_name', ''),
        "search_query": event_data.get('search_query', ''),
        "session_id": event_data.get('session_id'),
        "device_type": event_data.get('device_type', 'desktop'),
        "platform": event_data.get('platform', 'web'),
    }

    url = f"{settings.CPRP_API_URL}/api/event"
    try:
        # Assuming CPRP allows unauthenticated events or we need a service token. 
        # For now, CPRP requires JWT. In a real scenario, SmartShop backend needs a service token.
        # Let's hit the login endpoint first if needed, or assume a disabled auth for internal network.
        # For this prototype, we'll just send it. If it fails due to auth, we'll log it.
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=cprp_payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            UserEvent.objects.filter(event_id=event_data['event_id']).update(synced_to_cprp=True)
            logger.info(f"Successfully forwarded event {event_data['event_id']} to CPRP.")
        else:
            logger.warning(f"Failed to forward event to CPRP: {response.text}")
    except Exception as e:
        logger.error(f"Error forwarding event to CPRP: {e}")

class TrackEventView(generics.CreateAPIView):
    serializer_class = UserEventSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        if request.user.is_authenticated:
            data['user'] = request.user.id
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Async forward to CPRP
        threading.Thread(target=forward_to_cprp, args=(serializer.data,)).start()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
