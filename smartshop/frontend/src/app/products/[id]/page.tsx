"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useProductTracker } from "@/hooks/useTracker";
import { ShoppingCart, Star, Truck, ShieldCheck, Heart, Minus, Plus, ArrowLeft, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import { useCart } from "@/contexts/CartContext";
import { useWishlist } from "@/contexts/WishlistContext";
import { useAuth } from "@/contexts/AuthContext";

interface Feature {
  key: string;
  value: string;
}

interface Product {
  id: string;
  name: string;
  brand: string;
  price: string;
  compare_price: string | null;
  discount_percent: number | null;
  description: string | null;
  image_url: string | null;
  emoji: string | null;
  rating: string;
  review_count: number;
  stock_quantity: number;
  features: Feature[];
  category: { name: string; slug: string };
}

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { trackProductView, trackAddToCart } = useProductTracker();

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [addingToCart, setAddingToCart] = useState(false);
  const [cartSuccess, setCartSuccess] = useState(false);

  const { addToCart } = useCart();
  const { toggle, isInWishlist } = useWishlist();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (!id) return;
    api.get(`/products/${id}/`)
      .then(res => {
        setProduct(res.data);
        setLoading(false);
        trackProductView(res.data);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [id]);

  const handleAddToCart = async () => {
    if (!isAuthenticated) { router.push("/login"); return; }
    setAddingToCart(true);
    try {
      await addToCart(product!.id, quantity);
      trackAddToCart(product);
      setCartSuccess(true);
      setTimeout(() => setCartSuccess(false), 2500);
    } catch {
      alert("Failed to add to cart. Please try again.");
    } finally {
      setAddingToCart(false);
    }
  };

  const handleWishlistToggle = async () => {
    if (!isAuthenticated) { router.push("/login"); return; }
    await toggle(product!.id);
  };

  if (loading) {
    return <div className="container mx-auto px-4 py-16 flex justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div></div>;
  }

  if (!product) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold">Product not found</h1>
        <Link href="/products" className="mt-4 inline-flex items-center text-blue-600 hover:underline"><ArrowLeft size={16} className="mr-1" /> Back to Products</Link>
      </div>
    );
  }

  const inWishlist = isAuthenticated && isInWishlist(product.id);
  const price = parseFloat(product.price);
  const comparePrice = product.compare_price ? parseFloat(product.compare_price) : null;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6 flex items-center gap-2">
        <Link href="/" className="hover:text-blue-600">Home</Link>
        <span>/</span>
        <Link href="/products" className="hover:text-blue-600">Products</Link>
        <span>/</span>
        <Link href={`/products?category__slug=${product.category?.slug}`} className="hover:text-blue-600">{product.category?.name}</Link>
        <span>/</span>
        <span className="text-gray-900 truncate">{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* Product Image */}
        <div className="relative">
          <div className="bg-gray-50 rounded-2xl aspect-square flex items-center justify-center border border-gray-200 overflow-hidden group">
            <img 
              src="https://placehold.net/product-400x400.png"
              alt={product.name}
              className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500"
            />
            {product.discount_percent && (
              <div className="absolute top-4 left-4 bg-red-500 text-white text-sm font-bold px-2 py-1 rounded-lg">
                -{product.discount_percent}%
              </div>
            )}
          </div>
          {/* Wishlist button */}
          <button
            onClick={handleWishlistToggle}
            className={`absolute top-4 right-4 p-3 rounded-full shadow-md transition-all ${inWishlist ? "bg-red-500 text-white" : "bg-white text-gray-400 hover:text-red-500"}`}
          >
            <Heart size={20} fill={inWishlist ? "currentColor" : "none"} />
          </button>
        </div>

        {/* Product Info */}
        <div className="flex flex-col">
          <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">{product.brand}</p>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mt-1 mb-3">{product.name}</h1>

          {/* Rating */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex items-center bg-green-600 text-white text-sm font-bold px-2 py-0.5 rounded gap-1">
              <span>{parseFloat(product.rating).toFixed(1)}</span>
              <Star size={12} fill="currentColor" />
            </div>
            <span className="text-sm text-gray-500">{product.review_count.toLocaleString()} ratings</span>
          </div>

          {/* Price */}
          <div className="flex items-baseline gap-3 mb-6 pb-6 border-b border-gray-200">
            <span className="text-3xl font-bold text-gray-900">₹{price.toFixed(2)}</span>
            {comparePrice && (
              <>
                <span className="text-lg text-gray-400 line-through">₹{comparePrice.toFixed(2)}</span>
                <span className="text-green-600 font-semibold text-sm">{product.discount_percent}% off</span>
              </>
            )}
          </div>

          {/* Description */}
          <p className="text-gray-600 text-sm leading-relaxed mb-6">{product.description}</p>

          {/* Delivery Info */}
          <div className="space-y-2 mb-6">
            <div className="flex items-center text-sm text-gray-600 gap-2">
              <Truck className="h-4 w-4 text-blue-600" />
              <span>Free delivery on orders above ₹500 • Delivers in 2-3 days</span>
            </div>
            <div className="flex items-center text-sm text-gray-600 gap-2">
              <ShieldCheck className="h-4 w-4 text-blue-600" />
              <span>Genuine product guarantee • Secure checkout</span>
            </div>
          </div>

          {/* Quantity + CTA */}
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
              <button onClick={() => setQuantity(q => Math.max(1, q - 1))} className="px-3 py-2 hover:bg-gray-100 transition-colors"><Minus size={16} /></button>
              <span className="px-4 py-2 font-semibold border-x border-gray-300">{quantity}</span>
              <button onClick={() => setQuantity(q => Math.min(product.stock_quantity, q + 1))} className="px-3 py-2 hover:bg-gray-100 transition-colors"><Plus size={16} /></button>
            </div>
            <span className="text-sm text-gray-500">{product.stock_quantity} in stock</span>
          </div>

          <div className="flex gap-3">
            <button
              id="add-to-cart-btn"
              onClick={handleAddToCart}
              disabled={addingToCart || cartSuccess}
              className={`flex-1 flex items-center justify-center py-3.5 rounded-xl font-bold text-sm transition-all shadow-md ${
                cartSuccess
                  ? "bg-green-500 text-white"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              } disabled:opacity-70`}
            >
              {cartSuccess ? (
                <><CheckCircle className="mr-2" size={18} /> Added to Cart!</>
              ) : addingToCart ? (
                "Adding..."
              ) : (
                <><ShoppingCart className="mr-2" size={18} /> Add to Cart</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Product Features */}
      {product.features && product.features.length > 0 && (
        <div className="mt-10">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Product Details</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {product.features.map((feature, i) => (
              <div key={i} className={`flex px-5 py-3 text-sm ${i % 2 === 0 ? "bg-gray-50" : "bg-white"}`}>
                <span className="w-40 font-medium text-gray-600 flex-shrink-0">{feature.key}</span>
                <span className="text-gray-900">{feature.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
