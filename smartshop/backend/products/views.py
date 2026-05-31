from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'brand', 'cprp_price_range']
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['price', 'created_at']

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = 'id'

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
