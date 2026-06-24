import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class CPRPRecommendationView(APIView):
    """Proxy requests to the CPRP recommendation endpoint."""
    
    def get(self, request, user_id, *args, **kwargs):
        url = f"{settings.CPRP_API_URL}/profile/{user_id}"
        
        try:
            # We might need to login to CPRP to get a token, but for now assuming we bypass or have a service token.
            # In CPRP app.py, /api/login requires admin/admin123
            login_resp = requests.post(
                f"{settings.CPRP_API_URL}/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5
            )
            
            headers = {}
            if login_resp.status_code == 200:
                token = login_resp.json().get('token')
                headers['Authorization'] = f"Bearer {token}"
            
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                return Response(resp.json(), status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to fetch recommendations from CPRP"}, status=resp.status_code)
                
        except Exception as e:
            logger.error(f"Error fetching recommendations: {e}")
            return Response({"error": "Internal Error contacting CPRP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
