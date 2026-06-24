"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCart } from "@/contexts/CartContext";
import { useAuth } from "@/contexts/AuthContext";
import { Minus, Plus, Trash2, ShoppingBag, ArrowLeft, ShoppingCart } from "lucide-react";

export default function CartPage() {
  const { cart, isLoading, updateItem, removeItem, clearCart } = useCart();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [placing, setPlacing] = useState(false);

  if (authLoading) return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <ShoppingCart className="mx-auto h-16 w-16 text-gray-300 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your cart</h1>
        <p className="text-gray-500 mb-6">Please login to view your cart</p>
        <Link href="/login" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
          Login to Continue
        </Link>
      </div>
    );
  }

  const items = cart?.items || [];
  const total = cart ? parseFloat(cart.total_amount) : 0;

  const handlePlaceOrder = async () => {
    setPlacing(true);
    try {
      const { default: api } = await import("@/lib/api");
      const res = await api.post("/orders/", { shipping_address: "To be filled at checkout" });
      router.push(`/orders/${res.data.id}`);
    } catch {
      alert("Failed to place order. Please try again.");
    } finally {
      setPlacing(false);
    }
  };

  if (isLoading) {
    return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;
  }

  if (items.length === 0) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <ShoppingBag className="mx-auto h-20 w-20 text-gray-200 mb-6" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your cart is empty</h1>
        <p className="text-gray-500 mb-8">Add some items to get started!</p>
        <Link href="/products" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Shopping Cart ({cart?.total_items} items)</h1>
        <button onClick={() => clearCart()} className="text-sm text-red-500 hover:text-red-700 transition-colors">
          Clear Cart
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-3">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4">
              {/* Product Image */}
              <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center text-3xl flex-shrink-0">
                {item.product.emoji || "🛍️"}
              </div>

              {/* Product Info */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-blue-600 font-semibold uppercase">{item.product.brand}</p>
                <h3 className="font-semibold text-gray-900 truncate text-sm">{item.product.name}</h3>
                <p className="text-blue-700 font-bold mt-1">₹{parseFloat(item.product.price).toFixed(2)}</p>
              </div>

              {/* Quantity Controls */}
              <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
                <button
                  onClick={() => updateItem(item.id, item.quantity - 1)}
                  className="px-2.5 py-1.5 hover:bg-gray-100 transition-colors"
                >
                  <Minus size={14} />
                </button>
                <span className="px-3 py-1.5 text-sm font-semibold border-x border-gray-300">{item.quantity}</span>
                <button
                  onClick={() => updateItem(item.id, item.quantity + 1)}
                  className="px-2.5 py-1.5 hover:bg-gray-100 transition-colors"
                >
                  <Plus size={14} />
                </button>
              </div>

              {/* Subtotal */}
              <div className="text-right w-20 flex-shrink-0">
                <p className="font-bold text-gray-900">₹{parseFloat(item.subtotal).toFixed(2)}</p>
              </div>

              {/* Remove */}
              <button
                onClick={() => removeItem(item.id)}
                className="p-2 text-gray-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 p-6 sticky top-24">
            <h2 className="font-bold text-lg text-gray-900 mb-4">Order Summary</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal ({cart?.total_items} items)</span>
                <span>₹{total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Delivery</span>
                <span className="text-green-600 font-medium">{total >= 500 ? "FREE" : "₹49"}</span>
              </div>
              {total < 500 && (
                <p className="text-xs text-gray-400">Add ₹{(500 - total).toFixed(2)} more for free delivery</p>
              )}
              <div className="border-t border-gray-200 pt-3 flex justify-between font-bold text-gray-900">
                <span>Total Amount</span>
                <span>₹{(total + (total >= 500 ? 0 : 49)).toFixed(2)}</span>
              </div>
            </div>

            <button
              id="place-order-btn"
              onClick={handlePlaceOrder}
              disabled={placing}
              className="w-full mt-6 bg-orange-500 hover:bg-orange-600 text-white font-bold py-3.5 rounded-xl transition-colors disabled:opacity-70 text-sm"
            >
              {placing ? "Placing Order..." : "Place Order"}
            </button>
            <Link href="/products" className="block text-center mt-3 text-sm text-blue-600 hover:underline">
              Continue Shopping
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
