"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Filter, ChevronDown, ShoppingBag } from "lucide-react";
import api from "@/lib/api";

interface Category {
  id: number;
  name: string;
  slug: string;
}

interface Product {
  id: string;
  name: string;
  slug: string;
  brand: string;
  price: string;
  compare_price: string | null;
  image_url: string | null;
  category: Category;
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  useEffect(() => {
    // Fetch categories
    api.get("/products/categories/")
      .then(res => setCategories(res.data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    // Fetch products
    setLoading(true);
    let url = "/products/";
    if (selectedCategory) {
      url += `?category__slug=${selectedCategory}`;
    }
    
    api.get(url)
      .then(res => {
        setProducts(res.data.results || res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [selectedCategory]);

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">All Products</h1>
          <p className="text-muted-foreground mt-1">Showing {products.length} items</p>
        </div>
        
        <div className="mt-4 md:mt-0 flex items-center space-x-2">
          <button className="flex items-center space-x-2 bg-white border border-border px-4 py-2 rounded-lg text-sm font-medium hover:bg-muted transition-colors">
            <Filter size={16} />
            <span>Filter</span>
          </button>
          <div className="relative">
            <select 
              className="appearance-none bg-white border border-border pl-4 pr-10 py-2 rounded-lg text-sm font-medium hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {categories.map(c => (
                <option key={c.id} value={c.slug}>{c.name}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Sidebar Filters */}
        <div className="hidden md:block space-y-6">
          <div>
            <h3 className="font-semibold mb-4 border-b border-border pb-2">Categories</h3>
            <ul className="space-y-2">
              <li>
                <button 
                  onClick={() => setSelectedCategory("")}
                  className={`text-sm ${selectedCategory === "" ? "text-primary font-medium" : "text-muted-foreground hover:text-foreground"}`}
                >
                  All Products
                </button>
              </li>
              {categories.map(c => (
                <li key={c.id}>
                  <button 
                    onClick={() => setSelectedCategory(c.slug)}
                    className={`text-sm ${selectedCategory === c.slug ? "text-primary font-medium" : "text-muted-foreground hover:text-foreground"}`}
                  >
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
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20 bg-muted/30 rounded-2xl border border-border border-dashed">
              <ShoppingBag className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-foreground">No products found</h3>
              <p className="text-muted-foreground mt-1">Try selecting a different category or clear filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map(product => (
                <Link key={product.id} href={`/products/${product.id}`} className="group bg-white rounded-2xl border border-border overflow-hidden hover:border-primary/50 hover:shadow-lg transition-all duration-300">
                  <div className="aspect-[4/3] bg-muted relative overflow-hidden flex items-center justify-center">
                    {/* Placeholder for image */}
                    <span className="text-4xl">🧴</span>
                    <div className="absolute inset-0 bg-primary/0 group-hover:bg-primary/5 transition-colors" />
                  </div>
                  <div className="p-4">
                    <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">{product.brand}</p>
                    <h3 className="font-semibold text-foreground truncate">{product.name}</h3>
                    <div className="mt-2 flex items-center justify-between">
                      <div>
                        <span className="text-lg font-bold">${parseFloat(product.price).toFixed(2)}</span>
                        {product.compare_price && (
                          <span className="ml-2 text-sm text-muted-foreground line-through">
                            ${parseFloat(product.compare_price).toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
