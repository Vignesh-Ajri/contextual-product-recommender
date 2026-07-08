import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)

CPRP_URL = getattr(settings, "CPRP_API_URL", "http://localhost:5000")


class CPRPRecommendationView(APIView):
    """Get personalised recommendations for a logged-in user from CPRP."""
    permission_classes = [AllowAny]

    def get(self, request, user_id, *args, **kwargs):
        k = request.query_params.get("k", 8)
        url = f"{CPRP_URL}/recommend/{user_id}?k={k}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return Response(resp.json(), status=status.HTTP_200_OK)
            elif resp.status_code == 404:
                return Response({"error": "no_profile", "detail": "No profile found for this user yet."}, status=404)
            else:
                logger.warning("CPRP recommend returned %s: %s", resp.status_code, resp.text)
                return Response({"error": "cprp_error"}, status=resp.status_code)
        except Exception as e:
            logger.error("Error contacting CPRP recommend: %s", e)
            return Response({"error": "connection_error"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ColdStartRecommendationView(APIView):
    """Get cold-start recommendations by category (no user profile needed)."""
    permission_classes = [AllowAny]

    def get(self, request, category, *args, **kwargs):
        k = request.query_params.get("k", 8)
        brand = request.query_params.get("brand", "")
        price = request.query_params.get("price", "unknown")

        params = f"k={k}&price={price}"
        if brand:
            params += f"&brand={brand}"
        url = f"{CPRP_URL}/recommend/cold/{category}?{params}"

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return Response(resp.json(), status=status.HTTP_200_OK)
            else:
                logger.warning("CPRP cold-start returned %s: %s", resp.status_code, resp.text)
                return Response({"error": "cprp_error"}, status=resp.status_code)
        except Exception as e:
            logger.error("Error contacting CPRP cold-start: %s", e)
            return Response({"error": "connection_error"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
