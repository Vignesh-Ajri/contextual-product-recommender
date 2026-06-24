from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Wishlist, WishlistItem
from .serializers import UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer, WishlistSerializer, WishlistItemSerializer
from products.models import Product

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

class WishlistView(APIView):
    """GET the user's wishlist."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data)

class WishlistToggleView(APIView):
    """Add or remove a product from wishlist (toggle)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id, is_active=True)

        item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        if not created:
            item.delete()
            return Response({'message': 'Removed from wishlist', 'in_wishlist': False})
        return Response({'message': 'Added to wishlist', 'in_wishlist': True}, status=status.HTTP_201_CREATED)

class WishlistRemoveView(APIView):
    """Remove a specific item from wishlist."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_id):
        wishlist = get_object_or_404(Wishlist, user=request.user)
        item = get_object_or_404(WishlistItem, id=item_id, wishlist=wishlist)
        item.delete()
        return Response({'message': 'Removed from wishlist'})
