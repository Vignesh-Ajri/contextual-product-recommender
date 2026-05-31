import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { tracker } from '@/lib/tracker';

export function usePageViewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Track page view whenever the route changes
    const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '');
    
    tracker.track({
      event_type: 'page_view',
      page_url: window.location.origin + url,
    });
    
  }, [pathname, searchParams]);
}

export function useProductTracker() {
  return {
    trackProductView: (product: any) => {
      tracker.track({
        event_type: 'product_view',
        product_id: product.id,
        cprp_category: product.category?.cprp_category || '',
        cprp_brand: product.cprp_brand || product.brand,
        cprp_price_range: product.cprp_price_range || '',
        cprp_product_name: product.name,
      });
    },
    trackAddToCart: (product: any) => {
      tracker.track({
        event_type: 'cart_add',
        product_id: product.id,
        cprp_category: product.category?.cprp_category || '',
        cprp_brand: product.cprp_brand || product.brand,
        cprp_price_range: product.cprp_price_range || '',
      });
    }
  };
}
