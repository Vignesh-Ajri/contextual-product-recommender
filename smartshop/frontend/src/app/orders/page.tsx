"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { Package, ChevronRight, XCircle, CheckCircle, Clock, Truck } from "lucide-react";

interface OrderItem {
  id: string;
  product_name: string;
  product_brand: string;
  price_at_purchase: string;
  quantity: number;
  subtotal: string;
}

interface Order {
  id: string;
  status: string;
  total_amount: string;
  created_at: string;
  items: OrderItem[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  pending:    { label: "Pending",    color: "bg-yellow-100 text-yellow-700", icon: Clock },
  confirmed:  { label: "Confirmed",  color: "bg-blue-100 text-blue-700",    icon: CheckCircle },
  processing: { label: "Processing", color: "bg-purple-100 text-purple-700", icon: Package },
  shipped:    { label: "Shipped",    color: "bg-indigo-100 text-indigo-700", icon: Truck },
  delivered:  { label: "Delivered",  color: "bg-green-100 text-green-700",  icon: CheckCircle },
  cancelled:  { label: "Cancelled",  color: "bg-red-100 text-red-700",      icon: XCircle },
};

export default function OrdersPage() {
  const { isAuthenticated } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) { setIsLoading(false); return; }
    api.get("/orders/")
      .then(res => setOrders(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  const handleCancel = async (orderId: string) => {
    if (!confirm("Are you sure you want to cancel this order?")) return;
    setCancellingId(orderId);
    try {
      const res = await api.post(`/orders/${orderId}/cancel/`);
      setOrders(prev => prev.map(o => o.id === orderId ? res.data : o));
    } catch {
      alert("Could not cancel order. Please try again.");
    } finally {
      setCancellingId(null);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <Package className="mx-auto h-16 w-16 text-gray-200 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">My Orders</h1>
        <p className="text-gray-500 mb-6">Please login to view your orders</p>
        <Link href="/login" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
          Login to Continue
        </Link>
      </div>
    );
  }

  if (isLoading) return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Orders</h1>

      {orders.length === 0 ? (
        <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
          <Package className="mx-auto h-16 w-16 text-gray-200 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No orders yet</h2>
          <p className="text-gray-500 mb-6">Start shopping to see your orders here</p>
          <Link href="/products" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => {
            const statusCfg = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;
            const StatusIcon = statusCfg.icon;
            const canCancel = ["pending", "confirmed"].includes(order.status);

            return (
              <div key={order.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Order Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between px-5 py-4 border-b border-gray-100 gap-3">
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-xs text-gray-500">Order ID</p>
                      <p className="font-mono text-sm font-semibold text-gray-900">#{order.id.slice(0, 8).toUpperCase()}</p>
                    </div>
                    <div className="hidden sm:block h-8 w-px bg-gray-200" />
                    <div>
                      <p className="text-xs text-gray-500">Placed On</p>
                      <p className="text-sm font-medium text-gray-900">{new Date(order.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${statusCfg.color}`}>
                      <StatusIcon size={12} /> {statusCfg.label}
                    </span>
                    <span className="font-bold text-gray-900">₹{parseFloat(order.total_amount).toFixed(2)}</span>
                    {canCancel && (
                      <button
                        onClick={() => handleCancel(order.id)}
                        disabled={cancellingId === order.id}
                        className="text-xs text-red-500 hover:text-red-700 border border-red-300 hover:border-red-500 px-3 py-1 rounded-lg transition-colors disabled:opacity-60"
                      >
                        {cancellingId === order.id ? "Cancelling..." : "Cancel Order"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Order Items */}
                <div className="px-5 py-3 space-y-2">
                  {order.items.map((item) => (
                    <div key={item.id} className="flex items-center justify-between text-sm">
                      <div>
                        <span className="font-medium text-gray-900">{item.product_name}</span>
                        <span className="text-gray-500 ml-2">by {item.product_brand}</span>
                      </div>
                      <div className="text-gray-600">
                        {item.quantity} x ₹{parseFloat(item.price_at_purchase).toFixed(2)} = <span className="font-semibold text-gray-900">₹{parseFloat(item.subtotal).toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
