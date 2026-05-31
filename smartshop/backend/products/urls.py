from django.urls import path
from .views import ProductListView, ProductDetailView, CategoryListView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<uuid:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
]
