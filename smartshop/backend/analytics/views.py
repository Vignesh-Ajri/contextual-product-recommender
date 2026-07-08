import requests
import logging
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from .models import UserEvent
from .serializers import UserEventSerializer
import threading

logger = logging.getLogger(__name__)

def forward_to_cprp(event_data, user_email="", user_demographics=None, event_id=None):
    """Forward the event to the existing CPRP Flask API in a background thread."""
    if user_demographics is None:
        user_demographics = {}
        
    cprp_payload = {
        "user_id": str(event_data.get('user') or event_data.get('user_id') or event_data.get('session_id') or 'anonymous'),
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
        # Demographic and Location Data
        "age_group": user_demographics.get("age_group", ""),
        "gender": user_demographics.get("gender", ""),
        "city": user_demographics.get("city", ""),
        "state": user_demographics.get("state", ""),
        "country": user_demographics.get("country", "India"),
    }

    url = f"{settings.CPRP_API_URL}/event"
    try:
        response = requests.post(url, json=cprp_payload, timeout=5)
        if response.status_code in [200, 201]:
            logger.info("Successfully forwarded event to CPRP.")
            if event_id:
                from .models import UserEvent
                UserEvent.objects.filter(id=event_id).update(synced_to_cprp=True)
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
        user_demographics = {
            "age_group": "",
            "gender": "",
            "city": "",
            "state": "",
            "country": "India"
        }
        
        if request.user.is_authenticated:
            data['user'] = request.user.id
            user_email = request.user.email
            
            # Fetch address if it exists
            address = request.user.addresses.filter(is_default=True).first() or request.user.addresses.first()
            if address:
                user_demographics['city'] = address.city
                user_demographics['state'] = address.state
                user_demographics['country'] = address.country
            
            # Deterministically derive mock age/gender based on email hash for stable profiling
            email_hash_val = sum(ord(c) for c in user_email)
            genders = ["male", "female"]
            age_groups = ["18-24", "25-34", "35-44", "45-54"]
            
            user_demographics['gender'] = genders[email_hash_val % len(genders)]
            user_demographics['age_group'] = age_groups[email_hash_val % len(age_groups)]
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Async forward to CPRP
        threading.Thread(target=forward_to_cprp, args=(serializer.data, user_email, user_demographics, serializer.instance.id)).start()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecentEventsView(generics.ListAPIView):
    """Return the 30 most recent events from SQLite — used for live demo verification."""
    permission_classes = [AllowAny]
    serializer_class = UserEventSerializer

    def get_queryset(self):
        return UserEvent.objects.select_related('user').order_by('-timestamp')[:30]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = []
        for ev in qs:
            data.append({
                "id": str(ev.id),
                "event_type": ev.event_type,
                "user": ev.user.email if ev.user else None,
                "session_id": ev.session_id,
                "cprp_category": ev.cprp_category,
                "cprp_brand": ev.cprp_brand,
                "cprp_price_range": ev.cprp_price_range,
                "cprp_product_name": ev.cprp_product_name,
                "search_query": ev.search_query,
                "device_type": ev.device_type,
                "platform": ev.platform,
                "page_url": ev.page_url,
                "synced_to_cprp": ev.synced_to_cprp,
                "timestamp": ev.timestamp.isoformat(),
            })
        return Response({"count": len(data), "events": data})
