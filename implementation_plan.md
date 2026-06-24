# Epsilon-Style Omnichannel Engagement Platform Implementation

Based on the project outline and dataset recommendations you provided, this plan details how we can expand your existing `CPRP` repository into a fully-fledged **Unified Customer Identity Graph & Engagement Optimization Platform**.

## Goal Description

The goal is to evolve the current Contextual Product Recommender (`cprp`) into an enterprise-grade MarTech platform inspired by Epsilon's operations. We will build out 6 core modules covering data ingestion, identity resolution, Customer 360 profiling, personalization, attribution, and loyalty insights using industry-standard public datasets.

> [!NOTE]
> We have already laid the groundwork for this! The `db/schema_additions.sql` includes tables like `identity_confidence` and `engagement_patterns`, and `ml/epsilon_model.py` serves as the foundation for the Personalization Engine.

## Current State Assessment

Here is how your current repository maps to the 6 proposed modules:
*   **Module 1 (Data Integration)**: Partially implemented. You have a Kafka producer/consumer and are ingesting Kaggle 2019-Oct data and FMCG data.
*   **Module 2 (Identity Resolution)**: Foundation laid. `identities` and `identity_confidence` tables exist in `cprp` DB.
*   **Module 3 (Customer 360)**: Foundation laid. `users`, `user_demographics`, and `interest_profiles` tables exist.
*   **Module 4 (Personalization Engine)**: Partially implemented via `epsilon_model.py` (rich TF-IDF) and `recommend_engine.py`.
*   **Module 5 (Attribution)**: Not started.
*   **Module 6 (Loyalty Insights)**: Not started.

---

> [!IMPORTANT]
> ## User Review Required
> Please review the proposed roadmap below. Since this is a massive 3-month project, we need to decide which module to focus on next. I recommend starting with **Module 2 (Identity Resolution)** or **Module 1 (Dataset Ingestion)** for the new recommended datasets.

## Open Questions

1.  **Dataset Priority**: You have multiple datasets recommended (Criteo, Avazu, Dunnhumby). Would you like to start by writing scripts to download and process the **Identity Resolution datasets (Criteo/Avazu)** or the **Loyalty datasets (Dunnhumby)**?
2.  **Tech Stack Additions**: The proposal mentions adding Neo4j for the Graph DB and Airflow for ETL. Do you want to add these to our `docker-compose.yml`, or simulate them in Python/MySQL for now?

---

## Proposed Changes (Phased Roadmap)

### Phase 1: Advanced Identity Resolution & Customer 360 (Modules 2 & 3)
*   **Goal**: Connect fragmented user sessions into a unified identity graph.
*   **Action**: Integrate the **Criteo Cross-Device** or **Avazu** dataset to train probabilistic matching algorithms.
*   **Files to Modify/Create**:
    *   `[NEW]` `ml/identity_resolution.py`: ML script using fuzzy matching and Bayesian scoring to link device IDs, IPs, and emails.
    *   `[MODIFY]` `kafka/consumer.py`: Update the consumer to trigger the identity resolution logic on incoming events and update the `identity_confidence` table.

### Phase 2: Enhanced Personalization & Recommendation (Module 4)
*   **Goal**: Move beyond TF-IDF to Next Best Offer (NBO) models.
*   **Action**: Incorporate the **Instacart** or **Amazon Reviews** datasets for collaborative filtering and sequence modeling.
*   **Files to Modify/Create**:
    *   `[MODIFY]` `ml/epsilon_model.py`: Add an NBO engine using matrix factorization or sequence models.
    *   `[MODIFY]` `api/recommend_engine.py`: Integrate real-time Next Best Offer responses into the API.

### Phase 3: Campaign Attribution & Loyalty Insights (Modules 5 & 6)
*   **Goal**: Measure ROI and predict churn.
*   **Action**: Ingest the **Dunnhumby Loyalty** and **Criteo Display Ads** datasets.
*   **Files to Modify/Create**:
    *   `[NEW]` `db/loyalty_schema.sql`: Add tables for points, rewards, and ad impressions.
    *   `[NEW]` `ml/churn_prediction.py`: XGBoost model to predict user churn probability based on engagement decline.
    *   `[NEW]` `api/loyalty_routes.py`: Endpoints to serve CLV (Customer Lifetime Value) and Churn probability.
    *   `[MODIFY]` `dashboard.js` / `dashboard.html`: Add Loyalty Insights and Attribution ROI charts.

## Verification Plan

### Automated Tests
- Test identity resolution accuracy using validation splits from the Criteo dataset.
- Test churn model AUC-ROC on the Dunnhumby dataset.

### Manual Verification
- View the unified 360 profiles in the local `dashboard.html`.
- Run requests against the API to ensure the identity confidence scores accurately update when multiple identifiers are submitted.
