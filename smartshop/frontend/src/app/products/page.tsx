"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Filter, ChevronDown, ShoppingBag, Star, Heart } from "lucide-react";
import api from "@/lib/api";
import { useCart } from "@/contexts/CartContext";
import { useWishlist } from "@/contexts/WishlistContext";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

interface Category {
  id: number;
  name: string;
  slug: string;
  emoji: string | null;
}

interface Product {
  id: string;
  name: string;
  brand: string;
  price: string;
  compare_price: string | null;
  discount_percent: number | null;
  emoji: string | null;
  rating: string;
  review_count: number;
  stock_quantity: number;
  category: Category;
}

export default function ProductsPage() {
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>(searchParams.get("category__slug") || "");
  const [sortBy, setSortBy] = useState("default");
  const [addingToCart, setAddingToCart] = useState<string | null>(null);

  const { addToCart } = useCart();
  const { toggle, isInWishlist } = useWishlist();
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    api.get("/products/categories/")
      .then(res => {
        const data = res.data.results || res.data;
        setCategories(Array.isArray(data) ? data : []);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (selectedCategory) params.set("category__slug", selectedCategory);
    const searchQ = searchParams.get("search");
    if (searchQ) params.set("search", searchQ);
    if (sortBy === "price_asc") params.set("ordering", "price");
    if (sortBy === "price_desc") params.set("ordering", "-price");
    if (sortBy === "rating") params.set("ordering", "-rating");

    api.get(`/products/?${params.toString()}`)
      .then(res => setProducts(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedCategory, sortBy, searchParams]);

  const handleAddToCart = async (e: React.MouseEvent, productId: string) => {
    e.preventDefault();
    if (!isAuthenticated) { router.push("/login"); return; }
    setAddingToCart(productId);
    try {
      await addToCart(productId);
    } finally {
      setAddingToCart(null);
    }
  };

  const handleWishlistToggle = async (e: React.MouseEvent, productId: string) => {
    e.preventDefault();
    if (!isAuthenticated) { router.push("/login"); return; }
    await toggle(productId);
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Products</h1>
          <p className="text-gray-500 text-sm mt-0.5">{loading ? "Loading..." : `Showing ${products.length} products`}</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Category Filter */}
          <div className="relative">
            <select
              className="appearance-none bg-white border border-gray-300 rounded-lg pl-4 pr-8 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {categories.map(c => (
                <option key={c.id} value={c.slug}>{c.emoji} {c.name}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              className="appearance-none bg-white border border-gray-300 rounded-lg pl-4 pr-8 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="default">Sort: Relevance</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="rating">Top Rated</option>
            </select>
            <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Sidebar Categories */}
        <div className="hidden md:block">
          <div className="bg-white rounded-xl border border-gray-200 p-4 sticky top-24">
            <h3 className="font-bold text-gray-900 mb-3 text-sm uppercase tracking-wide">Categories</h3>
            <ul className="space-y-1">
              <li>
                <button
                  onClick={() => setSelectedCategory("")}
                  className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${selectedCategory === "" ? "bg-blue-50 text-blue-700 font-semibold" : "text-gray-600 hover:bg-gray-50"}`}
                >
                  All Products
                </button>
              </li>
              {categories.map(c => (
                <li key={c.id}>
                  <button
                    onClick={() => setSelectedCategory(c.slug)}
                    className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors flex items-center gap-2 ${selectedCategory === c.slug ? "bg-blue-50 text-blue-700 font-semibold" : "text-gray-600 hover:bg-gray-50"}`}
                  >
                    {c.emoji && <span>{c.emoji}</span>}
                    {c.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Product Grid */}
        <div className="md:col-span-3">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-pulse">
                  <div className="aspect-square bg-gray-200" />
                  <div className="p-4 space-y-2">
                    <div className="h-3 bg-gray-200 rounded w-1/3" />
                    <div className="h-4 bg-gray-200 rounded w-full" />
                    <div className="h-4 bg-gray-200 rounded w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
              <ShoppingBag className="mx-auto h-12 w-12 text-gray-300 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900">No products found</h3>
              <p className="text-gray-500 mt-1">Try a different category or clear filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((product) => {
                const inWishlist = isAuthenticated && isInWishlist(product.id);
                return (
                  <Link
                    key={product.id}
                    href={`/products/${product.id}`}
                    className="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg hover:border-blue-200 transition-all duration-300 flex flex-col"
                  >
                    {/* Image */}
                    <div className="relative aspect-square bg-gray-50 flex items-center justify-center group-hover:bg-blue-50 transition-colors">
                      <span className="text-6xl transform group-hover:scale-110 transition-transform duration-300">
                        {product.emoji || "🛍️"}
                      </span>
                      {product.discount_percent && (
                        <div className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded">
                          -{product.discount_percent}%
                        </div>
                      )}
                      <button
                        onClick={(e) => handleWishlistToggle(e, product.id)}
                        className={`absolute top-2 right-2 p-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-all ${inWishlist ? "opacity-100 bg-red-50 text-red-500" : "bg-white text-gray-400 hover:text-red-500"}`}
                      >
                        <Heart size={16} fill={inWishlist ? "currentColor" : "none"} />
                      </button>
                    </div>

                    {/* Info */}
                    <div className="p-4 flex flex-col flex-1">
                      <p className="text-xs font-semibold text-blue-600 uppercase">{product.brand}</p>
                      <h3 className="font-semibold text-gray-900 text-sm mt-0.5 line-clamp-2 flex-1">{product.name}</h3>

                      {/* Rating */}
                      <div className="flex items-center gap-1.5 mt-2">
                        <div className="flex items-center bg-green-600 text-white text-xs font-bold px-1.5 py-0.5 rounded gap-0.5">
                          <span>{parseFloat(product.rating).toFixed(1)}</span>
                          <Star size={9} fill="currentColor" />
                        </div>
                        <span className="text-xs text-gray-500">({product.review_count.toLocaleString()})</span>
                      </div>

                      {/* Price */}
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-lg font-bold text-gray-900">₹{parseFloat(product.price).toFixed(0)}</span>
                        {product.compare_price && (
                          <span className="text-xs text-gray-400 line-through">₹{parseFloat(product.compare_price).toFixed(0)}</span>
                        )}
                      </div>

                      {/* Add to Cart */}
                      <button
                        onClick={(e) => handleAddToCart(e, product.id)}
                        disabled={addingToCart === product.id}
                        className="mt-3 w-full flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors disabled:opacity-70"
                      >
                        {addingToCart === product.id ? "Adding..." : "+ Add to Cart"}
                      </button>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
