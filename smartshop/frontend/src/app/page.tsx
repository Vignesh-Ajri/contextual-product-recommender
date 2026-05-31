import Link from "next/link";
import { ArrowRight, Star, Truck, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-muted overflow-hidden py-20 lg:py-32">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent" />
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-2xl">
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-foreground mb-6">
              Everyday essentials, <br />
              <span className="text-primary">delivered to you.</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground mb-8 leading-relaxed">
              Discover premium personal care and FMCG products tailored to your lifestyle. Smart recommendations, fast shipping, and exclusive deals.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/products" className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-full text-white bg-primary hover:bg-primary/90 transition-colors shadow-lg shadow-primary/25">
                Shop Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link href="/categories" className="inline-flex items-center justify-center px-6 py-3 border border-border text-base font-medium rounded-full text-foreground bg-white hover:bg-muted transition-colors shadow-sm">
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
                <p className="text-sm text-muted-foreground">Free shipping on orders over $50</p>
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
                <Star className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Premium Quality</h3>
                <p className="text-sm text-muted-foreground">Top brands and verified products</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Placeholder for Dynamic Content (Products/Categories) */}
      <section className="py-16 md:py-24 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Trending Categories</h2>
          <p className="text-muted-foreground mb-12 max-w-2xl mx-auto">Explore our most popular collections curated just for you.</p>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
            {/* Category Cards (Placeholders for now) */}
            {['Skincare', 'Hair Care', 'Oral Care', 'Bath & Body'].map((cat) => (
              <Link key={cat} href={`/categories`} className="group block relative rounded-2xl overflow-hidden aspect-square border border-border bg-muted card-hover">
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10" />
                <div className="absolute inset-0 flex items-center justify-center bg-primary/5 group-hover:bg-primary/10 transition-colors" />
                <div className="absolute bottom-0 left-0 right-0 p-4 z-20 text-left">
                  <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">{cat}</h3>
                  <span className="text-white/80 text-sm flex items-center mt-1 opacity-0 group-hover:opacity-100 transition-opacity transform translate-y-2 group-hover:translate-y-0">
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
