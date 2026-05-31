"use client";

import Link from "next/link";
import { Search, ShoppingCart, User, Menu } from "lucide-react";
import { useState } from "react";

export default function Header() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full glass">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link href="/" className="text-2xl font-bold tracking-tighter text-primary">
              Smart<span className="text-foreground">Shop</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            <Link href="/products" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              All Products
            </Link>
            <Link href="/categories" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              Categories
            </Link>
            <Link href="/deals" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              Deals
            </Link>
          </nav>

          {/* Search Bar (Desktop) */}
          <div className="hidden md:flex flex-1 max-w-md mx-8 relative">
            <div className="relative w-full">
              <input
                type="text"
                placeholder="Search products..."
                className="w-full bg-muted/50 border border-border rounded-full py-2 pl-4 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow"
              />
              <button className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors">
                <Search size={18} />
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-4">
            <Link href="/profile" className="p-2 text-muted-foreground hover:text-primary hover:bg-muted rounded-full transition-all">
              <User size={20} />
            </Link>
            <Link href="/cart" className="p-2 text-muted-foreground hover:text-primary hover:bg-muted rounded-full transition-all relative">
              <ShoppingCart size={20} />
              <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none text-white bg-primary rounded-full transform translate-x-1/4 -translate-y-1/4">
                0
              </span>
            </Link>
            <button 
              className="md:hidden p-2 text-muted-foreground hover:bg-muted rounded-full"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <Menu size={24} />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-background">
          <div className="px-4 pt-2 pb-4 space-y-1">
            <div className="p-2">
              <div className="relative w-full">
                <input
                  type="text"
                  placeholder="Search products..."
                  className="w-full bg-muted border border-border rounded-lg py-2 pl-4 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <button className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <Search size={18} />
                </button>
              </div>
            </div>
            <Link href="/products" className="block px-3 py-2 rounded-md text-base font-medium text-foreground hover:bg-muted hover:text-primary">
              All Products
            </Link>
            <Link href="/categories" className="block px-3 py-2 rounded-md text-base font-medium text-foreground hover:bg-muted hover:text-primary">
              Categories
            </Link>
            <Link href="/deals" className="block px-3 py-2 rounded-md text-base font-medium text-foreground hover:bg-muted hover:text-primary">
              Deals
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
