"use client";

import Link from "next/link";
import { useWishlist } from "@/contexts/WishlistContext";
import { useAuth } from "@/contexts/AuthContext";
import { useCart } from "@/contexts/CartContext";
import { Heart, ShoppingCart, Trash2 } from "lucide-react";
import { useState } from "react";

export default function WishlistPage() {
  const { items, isLoading, removeItem } = useWishlist();
  const { isAuthenticated } = useAuth();
  const { addToCart } = useCart();
  const [addingToCart, setAddingToCart] = useState<string | null>(null);

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <Heart className="mx-auto h-16 w-16 text-gray-200 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your Wishlist</h1>
        <p className="text-gray-500 mb-6">Login to view and manage your wishlist</p>
        <Link href="/login" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
          Login to Continue
        </Link>
      </div>
    );
  }

  const handleAddToCart = async (productId: string) => {
    setAddingToCart(productId);
    try {
      await addToCart(productId);
    } finally {
      setAddingToCart(null);
    }
  };

  if (isLoading) return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        My Wishlist {items.length > 0 && <span className="text-gray-400 font-normal text-lg">({items.length} items)</span>}
      </h1>

      {items.length === 0 ? (
        <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
          <Heart className="mx-auto h-16 w-16 text-gray-200 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Your wishlist is empty</h2>
          <p className="text-gray-500 mb-6">Save items you love to revisit them later</p>
          <Link href="/products" className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow group">
              <Link href={`/products/${item.product.id}`}>
                <div className="aspect-square bg-gray-50 flex items-center justify-center text-5xl group-hover:bg-blue-50 transition-colors">
                  {(item.product as any).emoji || "🛍️"}
                </div>
              </Link>
              <div className="p-4">
                <p className="text-xs text-blue-600 font-semibold uppercase">{item.product.brand}</p>
                <Link href={`/products/${item.product.id}`}>
                  <h3 className="font-semibold text-gray-900 text-sm mt-0.5 hover:text-blue-600 transition-colors line-clamp-2">{item.product.name}</h3>
                </Link>
                <p className="font-bold text-gray-900 mt-2">₹{parseFloat(item.product.price).toFixed(2)}</p>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleAddToCart(item.product.id)}
                    disabled={addingToCart === item.product.id}
                    className="flex-1 flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors disabled:opacity-70"
                  >
                    <ShoppingCart size={13} className="mr-1" />
                    {addingToCart === item.product.id ? "Adding..." : "Add to Cart"}
                  </button>
                  <button
                    onClick={() => removeItem(item.id)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
