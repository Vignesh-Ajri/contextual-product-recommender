from rest_framework import serializers
from .models import Product, Category, ProductFeature

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'emoji', 'image_url']

class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = ['key', 'value']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    features = ProductFeatureSerializer(many=True, read_only=True)
    discount_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'brand',
            'price', 'compare_price', 'discount_percent', 'stock_quantity',
            'image_url', 'emoji', 'is_active', 'rating', 'review_count',
            'features', 'created_at'
        ]

    def get_discount_percent(self, obj):
        if obj.compare_price and obj.compare_price > obj.price:
            return int(((obj.compare_price - obj.price) / obj.compare_price) * 100)
        return None

class ProductListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    category = CategorySerializer(read_only=True)
    discount_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'brand', 'price', 'compare_price',
            'discount_percent', 'image_url', 'emoji', 'rating', 'review_count',
            'stock_quantity', 'category'
        ]

    def get_discount_percent(self, obj):
        if obj.compare_price and obj.compare_price > obj.price:
            return int(((obj.compare_price - obj.price) / obj.compare_price) * 100)
        return None
