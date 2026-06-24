"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { Package, Clock, CheckCircle, Truck, XCircle, ArrowLeft, Download, MapPin } from "lucide-react";

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
  shipping_address: string;
  notes: string;
  created_at: string;
  items: OrderItem[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any; step: number }> = {
  pending:    { label: "Order Placed",    color: "text-yellow-600", icon: Clock, step: 1 },
  confirmed:  { label: "Confirmed",       color: "text-blue-600",   icon: CheckCircle, step: 2 },
  processing: { label: "Processing",      color: "text-purple-600", icon: Package, step: 3 },
  shipped:    { label: "Shipped",         color: "text-indigo-600", icon: Truck, step: 4 },
  delivered:  { label: "Delivered",       color: "text-green-600",  icon: CheckCircle, step: 5 },
  cancelled:  { label: "Cancelled",       color: "text-red-600",    icon: XCircle, step: 0 },
};

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }

    api.get(`/orders/${id}/`)
      .then(res => {
        setOrder(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [id, isAuthenticated, authLoading, router]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this order?")) return;
    setCancelling(true);
    try {
      const res = await api.post(`/orders/${id}/cancel/`);
      setOrder(res.data);
    } catch {
      alert("Could not cancel order. Please try again.");
    } finally {
      setCancelling(false);
    }
  };

  if (loading || authLoading) {
    return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;
  }

  if (!order) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold">Order not found</h1>
        <Link href="/orders" className="mt-4 inline-flex items-center text-blue-600 hover:underline"><ArrowLeft size={16} className="mr-1" /> Back to My Orders</Link>
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusCfg.icon;
  const canCancel = ["pending", "confirmed"].includes(order.status);
  const subtotal = order.items.reduce((sum, item) => sum + parseFloat(item.subtotal), 0);
  const deliveryFee = parseFloat(order.total_amount) - subtotal;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 max-w-4xl">
      <Link href="/orders" className="inline-flex items-center text-sm text-gray-500 hover:text-blue-600 mb-6 transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Orders
      </Link>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
        {/* Header */}
        <div className="border-b border-gray-200 bg-gray-50 px-6 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Order #{order.id.slice(0, 8).toUpperCase()}</h1>
            <p className="text-sm text-gray-500 mt-1">Placed on {new Date(order.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold bg-white border border-gray-200 shadow-sm ${statusCfg.color}`}>
              <StatusIcon size={16} /> {statusCfg.label}
            </span>
            <button className="p-2 text-gray-500 hover:text-blue-600 bg-white border border-gray-200 rounded-lg hover:bg-blue-50 transition-colors" title="Download Invoice">
              <Download size={18} />
            </button>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Main Info */}
          <div className="md:col-span-2 space-y-8">
            {/* Progress Tracker (simplified) */}
            {order.status !== 'cancelled' && (
              <div className="relative pt-2 pb-6">
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded-full bg-gray-100">
                  <div style={{ width: `${(statusCfg.step / 5) * 100}%` }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-green-500 transition-all duration-500"></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500 font-medium">
                  <span className={statusCfg.step >= 1 ? "text-green-600" : ""}>Placed</span>
                  <span className={statusCfg.step >= 3 ? "text-green-600" : ""}>Processing</span>
                  <span className={statusCfg.step >= 5 ? "text-green-600" : ""}>Delivered</span>
                </div>
              </div>
            )}

            {/* Items */}
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4 border-b border-gray-100 pb-2">Items in Order</h2>
              <div className="space-y-4">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center text-xl">
                        🛍️
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">{item.product_name}</p>
                        <p className="text-sm text-gray-500">
                          {item.product_brand} • Qty: {item.quantity}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900">₹{parseFloat(item.subtotal).toFixed(2)}</p>
                      <p className="text-xs text-gray-500">₹{parseFloat(item.price_at_purchase).toFixed(2)} each</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar Info */}
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-gray-50 p-5 rounded-xl border border-gray-100">
              <h2 className="text-base font-bold text-gray-900 mb-4">Payment Summary</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-gray-600">
                  <span>Subtotal</span>
                  <span>₹{subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Delivery Fee</span>
                  <span>{deliveryFee > 0 ? `₹${deliveryFee.toFixed(2)}` : "Free"}</span>
                </div>
                <div className="border-t border-gray-200 pt-2 mt-2 flex justify-between font-bold text-gray-900 text-base">
                  <span>Total</span>
                  <span>₹{parseFloat(order.total_amount).toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Address */}
            <div>
              <h2 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-1.5">
                <MapPin size={16} className="text-gray-400" /> Shipping Address
              </h2>
              <p className="text-sm text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-100">
                {order.shipping_address || "No address provided during checkout."}
              </p>
            </div>

            {/* Actions */}
            {canCancel && (
              <div className="pt-4 border-t border-gray-100">
                <button
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="w-full text-center text-sm font-semibold text-red-600 border border-red-200 hover:bg-red-50 hover:border-red-300 py-2.5 rounded-lg transition-colors disabled:opacity-50"
                >
                  {cancelling ? "Cancelling..." : "Cancel Order"}
                </button>
                <p className="text-xs text-gray-400 text-center mt-2">You can only cancel before the order is processed.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
