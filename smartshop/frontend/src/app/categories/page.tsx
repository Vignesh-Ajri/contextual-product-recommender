"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import api from "@/lib/api";

interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  emoji: string | null;
}

const CATEGORY_COLORS = [
  "from-blue-400 to-blue-600",
  "from-purple-400 to-purple-600",
  "from-green-400 to-green-600",
  "from-orange-400 to-orange-600",
  "from-pink-400 to-pink-600",
];

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get("/products/categories/")
      .then(res => {
        const data = res.data.results || res.data;
        setCategories(Array.isArray(data) ? data : []);
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Shop by Category</h1>
        <p className="text-gray-500 mt-1">Browse all our daily essentials by category</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
        {categories.map((cat, i) => (
          <Link
            key={cat.id}
            href={`/products?category__slug=${cat.slug}`}
            className="group relative rounded-2xl overflow-hidden bg-gradient-to-br border border-gray-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
          >
            <div className={`absolute inset-0 bg-gradient-to-br ${CATEGORY_COLORS[i % CATEGORY_COLORS.length]} opacity-90`} />
            <div className="relative p-8 flex flex-col items-center justify-center text-center min-h-[180px]">
              <span className="text-6xl mb-4 drop-shadow-lg">{cat.emoji || "🛍️"}</span>
              <h2 className="text-2xl font-bold text-white">{cat.name}</h2>
              {cat.description && (
                <p className="text-white/80 text-sm mt-2 line-clamp-2">{cat.description}</p>
              )}
              <span className="mt-4 inline-flex items-center bg-white/20 hover:bg-white/30 text-white text-sm font-medium px-4 py-1.5 rounded-full transition-colors">
                Shop Now →
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
