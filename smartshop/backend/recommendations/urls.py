from django.urls import path
from .views import CPRPRecommendationView

urlpatterns = [
    path('<str:user_id>/', CPRPRecommendationView.as_view(), name='get_recommendations'),
]
