from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/recommendations/', include('recommendations.urls')),
]
