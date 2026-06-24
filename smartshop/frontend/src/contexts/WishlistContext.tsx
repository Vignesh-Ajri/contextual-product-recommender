"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import api from "@/lib/api";
import { useAuth } from "./AuthContext";

interface WishlistItem {
  id: string;
  product: {
    id: string;
    name: string;
    brand: string;
    price: string;
    emoji: string | null;
  };
  added_at: string;
}

interface WishlistContextType {
  items: WishlistItem[];
  isLoading: boolean;
  toggle: (productId: string) => Promise<{ in_wishlist: boolean }>;
  removeItem: (itemId: string) => Promise<void>;
  isInWishlist: (productId: string) => boolean;
  refreshWishlist: () => Promise<void>;
  totalItems: number;
}

const WishlistContext = createContext<WishlistContextType | null>(null);

export function WishlistProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refreshWishlist = useCallback(async () => {
    if (!isAuthenticated) { setItems([]); return; }
    try {
      setIsLoading(true);
      const res = await api.get("/auth/wishlist/");
      setItems(res.data.items || []);
    } catch {
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshWishlist();
  }, [refreshWishlist]);

  const toggle = async (productId: string) => {
    const res = await api.post("/auth/wishlist/toggle/", { product_id: productId });
    await refreshWishlist();
    return res.data;
  };

  const removeItem = async (itemId: string) => {
    await api.delete(`/auth/wishlist/items/${itemId}/`);
    await refreshWishlist();
  };

  const isInWishlist = (productId: string) =>
    items.some((item) => item.product.id === productId);

  return (
    <WishlistContext.Provider value={{ items, isLoading, toggle, removeItem, isInWishlist, refreshWishlist, totalItems: items.length }}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error("useWishlist must be used within WishlistProvider");
  return ctx;
}
