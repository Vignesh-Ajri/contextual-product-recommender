from django.urls import path
from .views import (
    CartView, CartItemAddView, CartItemUpdateView,
    OrderListCreateView, OrderDetailView, OrderCancelView
)

urlpatterns = [
    # Cart endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartItemAddView.as_view(), name='cart-add'),
    path('cart/items/<uuid:item_id>/', CartItemUpdateView.as_view(), name='cart-item-update'),

    # Order endpoints
    path('', OrderListCreateView.as_view(), name='order-list-create'),
    path('<uuid:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
