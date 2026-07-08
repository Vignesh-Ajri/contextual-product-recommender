# CPRP & SmartShop API Documentation

This document lists all the API endpoints available in the Contextual Product Recommender Platform (CPRP) and the SmartShop Django backend.

## 1. SmartShop Backend (Django)
**Base URL:** `http://localhost:8000`

The Django backend serves the Next.js frontend, manages the local SQLite database for basic e-commerce functionality, and acts as a proxy to the CPRP recommendation engine.

### 🔐 Authentication
* **`POST http://localhost:8000/api/auth/login/`**
  Authenticates a user and returns a JWT token.
* **`POST http://localhost:8000/api/auth/register/`**
  Registers a new user account.

### 🛍️ Products & Orders
* **`GET http://localhost:8000/api/products/`**
  Lists all SmartShop products (supports pagination).
* **`GET http://localhost:8000/api/products/categories/`**
  Lists all product categories.
* **`GET http://localhost:8000/api/products/{id}/`**
  Gets detailed information for a specific product.
* **`GET|POST http://localhost:8000/api/orders/`**
  Manages user orders and checkout flow.
* **`GET|POST http://localhost:8000/api/reviews/`**
  Manages product reviews.

### 📊 Analytics & Tracking (Demo Features)
* **`POST http://localhost:8000/api/analytics/track/`**
  Receives tracking events (views, cart adds, purchases) from the Next.js frontend and forwards them to CPRP via API/Kafka.
* **`GET http://localhost:8000/api/analytics/events/`**
  Returns the 30 most recent user events from SQLite. Excellent for live demo verification to show that user interactions are being captured in real-time.

### ✨ Recommendations (Proxy to CPRP)
* **`GET http://localhost:8000/api/recommendations/{user_id}/`**
  Fetches AI-powered personalized recommendations for a logged-in user from the CPRP engine.
* **`GET http://localhost:8000/api/recommendations/cold/{category}/`**
  Fetches cold-start recommendations (trending products) for a specific category when the user has no history or is not logged in.

---

## 2. CPRP Recommendation Engine (FastAPI)
**Base URL:** `http://localhost:5000`

The FastAPI backend handles the heavy lifting: ingesting Kafka events, maintaining ML interest profiles in MySQL, and serving the AI recommendations.

### 🧠 Core Recommendation Engine
* **`GET http://localhost:5000/`**
  Root endpoint returning project details and active ML model info.
* **`GET http://localhost:5000/health`**
  Checks the health status of the ML model, MySQL, Redis cache, and Kafka cluster.
* **`GET http://localhost:5000/recommend/{user_id}`**
  Returns personalized product recommendations based on the user's highest interest score and past activity.
* **`GET http://localhost:5000/recommend/cold/{category}`**
  Returns general cold-start recommendations for a specific category.

### 📡 Data Ingestion
* **`POST http://localhost:5000/event`**
  Ingests a user event and publishes it to the Kafka `user_events` topic to update their interest profile. (Has a direct MySQL fallback if Kafka is down).
* **`GET http://localhost:5000/api/v1/pixel.gif`**
  A 1x1 transparent tracking pixel for collecting analytics via a simple image request, supporting cookie-based tracking.

### 👤 User Profiles & Catalog
* **`GET http://localhost:5000/profile/{user_id}`**
  Returns the full MySQL interest profile, demographic data, and interaction counts for a specific user.
* **`GET http://localhost:5000/catalog/categories`**
  Lists all known product categories in the CPRP ML engine.
* **`GET http://localhost:5000/catalog/brands`**
  Lists all known product brands.

### ⚙️ Admin Dashboard & Diagnostics
* **`GET http://localhost:5000/metrics`**
  Evaluates model health on the fly and returns live Precision, Recall, F1, and NDCG scores based on a sample of products.
* **`GET http://localhost:5000/api/admin/stats`**
  Provides overall statistics (total users, profiled users, active alerts) for the admin dashboard.
* **`GET http://localhost:5000/api/admin/profiles`**
  Lists all user interest profiles sorted by highest interest score.
* **`GET http://localhost:5000/api/admin/activity`**
  Provides a feed of the most recent interaction activity across the platform.
* **`GET http://localhost:5000/api/admin/lifetimes`**
  Lists all configured product lifetime days (used for replenishment alerts).
* **`PUT http://localhost:5000/api/admin/lifetimes/{category}`**
  Updates the product lifetime configuration for a specific category.
