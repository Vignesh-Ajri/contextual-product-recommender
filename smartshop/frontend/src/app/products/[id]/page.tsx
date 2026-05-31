"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useProductTracker } from "@/hooks/useTracker";
import { ShoppingCart, Star, Truck, ShieldCheck, Heart } from "lucide-react";
import api from "@/lib/api";

export default function ProductDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { trackProductView, trackAddToCart } = useProductTracker();
  
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [addingToCart, setAddingToCart] = useState(false);

  useEffect(() => {
    if (!id) return;
    
    api.get(`/products/${id}/`)
      .then(res => {
        setProduct(res.data);
        setLoading(false);
        // Track the view!
        trackProductView(res.data);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [id]);

  const handleAddToCart = () => {
    setAddingToCart(true);
    trackAddToCart(product);
    
    // Simulate adding to cart
    setTimeout(() => {
      setAddingToCart(false);
      alert("Added to cart!");
    }, 500);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-16 flex justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold">Product not found</h1>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-16">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* Product Image */}
        <div className="bg-muted rounded-3xl aspect-square flex items-center justify-center border border-border p-8 relative overflow-hidden group">
          <span className="text-9xl transform group-hover:scale-110 transition-transform duration-500">🧴</span>
          <button className="absolute top-6 right-6 p-3 bg-white/80 backdrop-blur-md rounded-full text-muted-foreground hover:text-red-500 transition-colors shadow-sm">
            <Heart size={24} />
          </button>
        </div>

        {/* Product Info */}
        <div className="flex flex-col">
          <nav className="text-sm text-muted-foreground mb-4 flex items-center space-x-2">
            <span>Home</span>
            <span>/</span>
            <span>{product.category?.name}</span>
          </nav>
          
          <p className="text-sm font-semibold text-primary uppercase tracking-wider mb-2">{product.brand}</p>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">{product.name}</h1>
          
          <div className="flex items-center space-x-4 mb-6">
            <div className="flex items-center text-accent">
              {[1,2,3,4,5].map(i => <Star key={i} size={18} fill="currentColor" />)}
            </div>
            <span className="text-sm text-muted-foreground">(24 reviews)</span>
          </div>
          
          <div className="flex items-baseline space-x-3 mb-8">
            <span className="text-4xl font-bold text-foreground">${parseFloat(product.price).toFixed(2)}</span>
            {product.compare_price && (
              <span className="text-xl text-muted-foreground line-through">
                ${parseFloat(product.compare_price).toFixed(2)}
              </span>
            )}
          </div>
          
          <p className="text-muted-foreground mb-8 leading-relaxed">
            {product.description || `Premium quality ${product.name} by ${product.brand}. Specially formulated to provide the best care for your daily needs.`}
          </p>
          
          <div className="mb-8 space-y-4 border-y border-border py-6">
            <div className="flex items-center text-sm">
              <Truck className="h-5 w-5 text-primary mr-3" />
              <span className="text-muted-foreground">Free shipping on orders over $50. Delivers in 2-3 days.</span>
            </div>
            <div className="flex items-center text-sm">
              <ShieldCheck className="h-5 w-5 text-primary mr-3" />
              <span className="text-muted-foreground">Genuine product guarantee. Secure checkout.</span>
            </div>
          </div>
          
          <div className="flex space-x-4 mt-auto">
            <button 
              onClick={handleAddToCart}
              disabled={addingToCart}
              className="flex-1 bg-primary hover:bg-primary/90 text-white py-4 px-8 rounded-xl font-bold text-lg flex items-center justify-center transition-all shadow-lg shadow-primary/25 disabled:opacity-70"
            >
              <ShoppingCart className="mr-2" />
              {addingToCart ? "Adding..." : "Add to Cart"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
