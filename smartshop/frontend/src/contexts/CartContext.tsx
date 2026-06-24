"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import api from "@/lib/api";
import { useAuth } from "./AuthContext";

interface Product {
  id: string;
  name: string;
  brand: string;
  price: string;
  compare_price: string | null;
  emoji: string | null;
  image_url: string | null;
}

interface CartItem {
  id: string;
  product: Product;
  quantity: number;
  subtotal: string;
}

interface Cart {
  id: string;
  items: CartItem[];
  total_amount: string;
  total_items: number;
}

interface CartContextType {
  cart: Cart | null;
  isLoading: boolean;
  addToCart: (productId: string, quantity?: number) => Promise<void>;
  updateItem: (itemId: string, quantity: number) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
  clearCart: () => Promise<void>;
  refreshCart: () => Promise<void>;
  totalItems: number;
}

const CartContext = createContext<CartContextType | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refreshCart = useCallback(async () => {
    if (!isAuthenticated) { setCart(null); return; }
    try {
      setIsLoading(true);
      const res = await api.get("/orders/cart/");
      setCart(res.data);
    } catch {
      setCart(null);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const addToCart = async (productId: string, quantity = 1) => {
    await api.post("/orders/cart/add/", { product_id: productId, quantity });
    await refreshCart();
  };

  const updateItem = async (itemId: string, quantity: number) => {
    await api.patch(`/orders/cart/items/${itemId}/`, { quantity });
    await refreshCart();
  };

  const removeItem = async (itemId: string) => {
    await api.delete(`/orders/cart/items/${itemId}/`);
    await refreshCart();
  };

  const clearCart = async () => {
    await api.delete("/orders/cart/");
    await refreshCart();
  };

  const totalItems = cart?.total_items ?? 0;

  return (
    <CartContext.Provider value={{ cart, isLoading, addToCart, updateItem, removeItem, clearCart, refreshCart, totalItems }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
