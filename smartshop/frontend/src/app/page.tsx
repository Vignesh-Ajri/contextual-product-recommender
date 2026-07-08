"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, Star, ShoppingBag, Truck, ShieldCheck, Sparkles, Zap } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useCart } from "@/contexts/CartContext";
import { tracker } from "@/lib/tracker";

interface CprpRecommendation {
  product_name: string;
  main_category: string;
  brand: string;
  price_range: string;
  score?: number;
}

interface SmartshopProduct {
  id: string;
  name: string;
  brand: string;
  price: string;
  image_url: string | null;
  emoji: string | null;
  rating: string;
  review_count: number;
  category: { name: string; slug: string };
}

const COLD_CATEGORIES = ["mouthwash", "face_wash", "shampoo", "lipstick", "moisturizer", "detergent"];

export default function Home() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { addToCart } = useCart();

  const [recs, setRecs] = useState<CprpRecommendation[]>([]);
  const [products, setProducts] = useState<SmartshopProduct[]>([]);
  const [recsLoading, setRecsLoading] = useState(true);
  const [recSource, setRecSource] = useState<"personalised" | "cold_start" | "none">("none");
  const [addingId, setAddingId] = useState<string | null>(null);

  // Fetch CPRP recommendations once auth state resolves
  useEffect(() => {
    if (authLoading) return;

    const fetchRecs = async () => {
      setRecsLoading(true);
      try {
        if (isAuthenticated && user) {
          // Personalised recommendations
          const res = await api.get(`/recommendations/${user.id}/?k=8`);
          const data = res.data;
          if (data.recommendations && data.recommendations.length > 0) {
            setRecs(data.recommendations);
            setRecSource("personalised");
            return;
          }
        }

        // Cold-start: pick a random category to avoid same results every time
        const cat = COLD_CATEGORIES[Math.floor(Math.random() * COLD_CATEGORIES.length)];
        const res = await api.get(`/recommendations/cold/${cat}/?k=8`);
        const data = res.data;
        if (data.recommendations && data.recommendations.length > 0) {
          setRecs(data.recommendations);
          setRecSource("cold_start");
        }
      } catch (err) {
        console.error("Failed to load CPRP recommendations:", err);
      } finally {
        setRecsLoading(false);
      }
    };

    fetchRecs();
  }, [isAuthenticated, user, authLoading]);

  // Match CPRP recs to actual SmartShop products by name/brand for cart + display
  useEffect(() => {
    if (recs.length === 0) return;

    const fetchMatchedProducts = async () => {
      try {
        // Fetch all products and fuzzy-match by category / brand
        const res = await api.get("/products/?page_size=200");
        const allProducts: SmartshopProduct[] = res.data.results || res.data;

        // Build a prioritised list matching CPRP recommendations
        const matched: SmartshopProduct[] = [];
        const seen = new Set<string>();

        for (const rec of recs) {
          const found = allProducts.find(
            (p) =>
              !seen.has(p.id) &&
              (p.brand.toLowerCase().includes(rec.brand.toLowerCase()) ||
                p.category.slug.includes(rec.main_category.replace("_", "-")) ||
                p.category.name.toLowerCase().includes(rec.main_category.replace("_", " ")))
          );
          if (found) {
            matched.push(found);
            seen.add(found.id);
          }
        }

        // Pad with popular items if not enough matches
        if (matched.length < 4) {
          for (const p of allProducts) {
            if (!seen.has(p.id)) {
              matched.push(p);
              seen.add(p.id);
              if (matched.length >= 8) break;
            }
          }
        }

        setProducts(matched.slice(0, 8));
      } catch (err) {
        console.error("Failed to fetch matched products:", err);
      }
    };

    fetchMatchedProducts();
  }, [recs]);

  const handleAddToCart = async (e: React.MouseEvent, product: SmartshopProduct) => {
    e.preventDefault();
    setAddingId(product.id);
    try {
      await addToCart(product.id);
      // Track the cart event
      tracker.track({
        event_type: "cart_add",
        product_id: product.id,
        cprp_category: product.category.slug.replace("-", "_"),
        cprp_brand: product.brand.toLowerCase(),
        cprp_product_name: product.name,
        page_url: window.location.href,
        referrer: document.referrer,
        device_type: "desktop",
        platform: "web",
      });
    } catch {
      // Redirect to login handled by CartContext
    } finally {
      setAddingId(null);
    }
  };

  const sectionTitle =
    recSource === "personalised"
      ? `✨ Recommended for You`
      : recSource === "cold_start"
      ? "🔥 Trending on SmartShop"
      : "🛍️ Popular Products";

  const sectionSubtitle =
    recSource === "personalised"
      ? "AI-powered picks based on your browsing and purchase history."
      : "Personalised picks by CPRP — no account needed.";

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-muted overflow-hidden py-20 lg:py-32">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent" />
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
              <Sparkles size={14} />
              AI-Powered Recommendations
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-foreground mb-6">
              Everyday essentials, <br />
              <span className="text-primary">delivered to you.</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground mb-8 leading-relaxed">
              Discover premium personal care and FMCG products tailored to your lifestyle. Smart recommendations, fast shipping, and exclusive deals.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                href="/products"
                className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-full text-white bg-primary hover:bg-primary/90 transition-colors shadow-lg shadow-primary/25"
              >
                Shop Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                href="/categories"
                className="inline-flex items-center justify-center px-6 py-3 border border-border text-base font-medium rounded-full text-foreground bg-white hover:bg-muted transition-colors shadow-sm"
              >
                Browse Categories
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Value Props */}
      <section className="py-12 bg-white border-b border-border">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-full text-primary">
                <Truck className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Fast Delivery</h3>
                <p className="text-sm text-muted-foreground">Free shipping on orders over ₹500</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-full text-primary">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Secure Payments</h3>
                <p className="text-sm text-muted-foreground">100% secure checkout process</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-primary/10 rounded-full text-primary">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Smart Picks</h3>
                <p className="text-sm text-muted-foreground">AI engine learns your preferences</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CPRP Recommendations Section */}
      <section className="py-16 md:py-24 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-10">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-foreground">{sectionTitle}</h2>
              <p className="text-muted-foreground mt-1">{sectionSubtitle}</p>
            </div>
            <Link
              href="/products"
              className="hidden sm:inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
            >
              View all <ArrowRight size={14} />
            </Link>
          </div>

          {recsLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-pulse">
                  <div className="aspect-square bg-gray-100" />
                  <div className="p-4 space-y-2">
                    <div className="h-3 bg-gray-200 rounded w-1/2" />
                    <div className="h-4 bg-gray-200 rounded w-full" />
                    <div className="h-4 bg-gray-200 rounded w-3/4" />
                    <div className="h-8 bg-gray-200 rounded mt-2" />
                  </div>
                </div>
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
              <ShoppingBag className="mx-auto h-12 w-12 text-gray-300 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900">No recommendations yet</h3>
              <p className="text-gray-500 mt-1">Browse some products and our AI will personalise your feed.</p>
              <Link
                href="/products"
                className="mt-4 inline-flex items-center text-sm font-semibold text-primary hover:underline"
              >
                Start browsing <ArrowRight size={14} className="ml-1" />
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map((product) => (
                <Link
                  key={product.id}
                  href={`/products/${product.id}`}
                  className="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg hover:border-blue-200 transition-all duration-300 flex flex-col"
                >
                  {/* Image */}
                  <div className="relative aspect-square bg-gray-50 flex items-center justify-center group-hover:bg-blue-50 transition-colors overflow-hidden">
                    <img 
                      src="https://placehold.net/product-400x400.png"
                      alt={product.name}
                      className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-300"
                    />
                    {recSource === "personalised" && (
                      <div className="absolute top-2 left-2 bg-gradient-to-r from-blue-600 to-violet-600 text-white text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Sparkles size={9} /> For You
                      </div>
                    )}
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
                    <div className="mt-2">
                      <span className="text-lg font-bold text-gray-900">₹{parseFloat(product.price).toFixed(0)}</span>
                    </div>

                    {/* Add to Cart */}
                    <button
                      onClick={(e) => handleAddToCart(e, product)}
                      disabled={addingId === product.id}
                      className="mt-3 w-full flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors disabled:opacity-70"
                    >
                      {addingId === product.id ? "Adding..." : "+ Add to Cart"}
                    </button>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Category Grid */}
      <section className="py-16 md:py-24 bg-muted/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Trending Categories</h2>
          <p className="text-muted-foreground mb-12 max-w-2xl mx-auto">Explore our most popular collections curated just for you.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
            {[
              { name: "Skincare", emoji: "🧴" },
              { name: "Hair Care", emoji: "💇" },
              { name: "Oral Care", emoji: "🪥" },
              { name: "Bath & Body", emoji: "🛁" },
            ].map((cat) => (
              <Link
                key={cat.name}
                href="/categories"
                className="group block relative rounded-2xl overflow-hidden aspect-square border border-border bg-white card-hover"
              >
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10" />
                <div className="absolute inset-0 flex items-center justify-center text-6xl group-hover:scale-110 transition-transform duration-300">
                  {cat.emoji}
                </div>
                <div className="absolute bottom-0 left-0 right-0 p-4 z-20 text-left">
                  <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">{cat.name}</h3>
                  <span className="text-white/80 text-sm flex items-center mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    Explore <ArrowRight className="ml-1 h-4 w-4" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
