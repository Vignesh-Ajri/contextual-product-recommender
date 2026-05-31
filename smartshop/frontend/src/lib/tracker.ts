import api from './api';

// Define the event structure
export interface TrackingEvent {
  event_type: 'page_view' | 'product_view' | 'search' | 'cart_add' | 'cart_remove' | 'purchase' | 'click' | 'dismiss';
  product_id?: string;
  category_id?: number;
  cprp_category?: string;
  cprp_brand?: string;
  cprp_price_range?: string;
  cprp_product_name?: string;
  search_query?: string;
  page_url: string;
  referrer: string;
  device_type: string;
  platform: string;
}

class EventTracker {
  private sessionId: string;
  private deviceType: string;

  constructor() {
    this.sessionId = this.getOrCreateSessionId();
    this.deviceType = this.detectDeviceType();
  }

  private getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return 'server-side';
    let sid = sessionStorage.getItem('smartshop_session');
    if (!sid) {
      // In a real app, you'd use a robust UUID. For this frontend we'll use crypto or a simple generator.
      // Next.js polyfills crypto in edge, but let's just use a simple string for this MVP.
      sid = `sess_${Math.random().toString(36).substring(2, 15)}_${Date.now()}`;
      sessionStorage.setItem('smartshop_session', sid);
    }
    return sid;
  }

  private detectDeviceType(): string {
    if (typeof window === 'undefined') return 'desktop';
    const ua = navigator.userAgent;
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) return 'tablet';
    if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/.test(ua)) return 'mobile';
    return 'desktop';
  }

  public async track(eventData: Partial<TrackingEvent>) {
    if (typeof window === 'undefined') return;

    const payload = {
      event_id: `evt_${Math.random().toString(36).substring(2, 15)}_${Date.now()}`,
      session_id: this.sessionId,
      device_type: this.deviceType,
      platform: 'web',
      page_url: window.location.href,
      referrer: document.referrer,
      ...eventData
    };

    try {
      // Send to Django backend (which forwards to CPRP Flask backend)
      await api.post('/analytics/track/', payload);
      if (process.env.NODE_ENV === 'development') {
        console.log('Tracked Event:', payload);
      }
    } catch (error) {
      console.error('Failed to track event:', error);
    }
  }
}

// Singleton instance
export const tracker = new EventTracker();
