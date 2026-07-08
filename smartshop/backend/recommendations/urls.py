from django.urls import path
from .views import CPRPRecommendationView, ColdStartRecommendationView

urlpatterns = [
    path('<str:user_id>/', CPRPRecommendationView.as_view(), name='get_recommendations'),
    path('cold/<str:category>/', ColdStartRecommendationView.as_view(), name='cold_start_recommendations'),
]
