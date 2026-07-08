import pandas as pd
import networkx as nx
import uuid
import os
import joblib

print("=" * 55)
print("  CPRP — Advanced Identity Resolution")
print("=" * 55)

print("\n1. Loading identity events dataset...")
try:
    df = pd.read_csv("data/synthetic_identity_events.csv")
    print(f"  Loaded {len(df):,} events.")
except FileNotFoundError:
    print("  Dataset not found. Run: python data/generate_identity_data.py")
    exit(1)

# ── 2. Build the Identity Graph ─────────────────────────────────
print("\n2. Building the Identity Graph (NetworkX)...")
G = nx.Graph()

for _, row in df.iterrows():
    identifiers = []
    if pd.notna(row.get('device_id')):
        identifiers.append(("device", row['device_id']))
    if pd.notna(row.get('ip_address')):
        identifiers.append(("ip", row['ip_address']))
    if pd.notna(row.get('email_hash')):
        identifiers.append(("email", row['email_hash']))
    if pd.notna(row.get('loyalty_id')):
        identifiers.append(("loyalty", row['loyalty_id']))
        
    # Add nodes and edges between all identifiers in this event
    for i in range(len(identifiers)):
        G.add_node(identifiers[i])
        for j in range(i + 1, len(identifiers)):
            # Weight could represent frequency of co-occurrence
            if G.has_edge(identifiers[i], identifiers[j]):
                G[identifiers[i]][identifiers[j]]['weight'] += 1
            else:
                G.add_edge(identifiers[i], identifiers[j], weight=1)

print(f"  Graph Nodes: {G.number_of_nodes():,}")
print(f"  Graph Edges: {G.number_of_edges():,}")

# ── 3. Resolve Identities (Connected Components) ────────────────
print("\n3. Resolving Identities (Connected Components)...")

# A component is a unified person
components = list(nx.connected_components(G))
print(f"  Total Unique Users Identified: {len(components):,}")

# Assign a universal core_id to each component
identity_map = {}
confidence_records = []

for component in components:
    core_id = str(uuid.uuid4())
    
    types_found = set(node[0] for node in component)
    
    # Calculate a rough confidence score
    # High if we have a deterministic anchor (email, loyalty)
    # Medium if we have multiple devices but no anchor
    # Low if it's just a single IP or single device
    confidence = 0.3
    if "email" in types_found or "loyalty" in types_found:
        confidence = 0.9
    elif "device" in types_found and len(component) > 1:
        confidence = 0.6
        
    confidence_records.append({
        "core_id": core_id,
        "match_signals": ",".join(types_found),
        "confidence_score": confidence,
        "resolution_type": "deterministic" if confidence > 0.8 else "probabilistic",
        "node_count": len(component)
    })
    
    for node in component:
        identity_map[node] = core_id

# ── 4. Save the Mappings ────────────────────────────────────────
print("\n4. Saving Identity Graph Mappings...")

os.makedirs("ml", exist_ok=True)

# Save the map for fast API lookup
joblib.dump(identity_map, "ml/identity_graph_map.pkl")
print("  Saved ml/identity_graph_map.pkl")

# Save the confidence scores to load into the DB
conf_df = pd.DataFrame(confidence_records)
conf_df.to_csv("data/identity_confidence.csv", index=False)
print("  Saved data/identity_confidence.csv")

# Print some stats
print("\nStats:")
print(f"  High Confidence Profiles  : {len(conf_df[conf_df['confidence_score'] > 0.8]):,}")
print(f"  Medium Confidence Profiles: {len(conf_df[conf_df['confidence_score'] == 0.6]):,}")
print(f"  Low Confidence Profiles   : {len(conf_df[conf_df['confidence_score'] < 0.5]):,}")

print("\n── Done ─────────────────────────────────────────────")
