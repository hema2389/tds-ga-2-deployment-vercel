import pandas as pd
import numpy as np
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- FastAPI Setup ---
app = FastAPI()

# Enable CORS for requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # allow all origins
    allow_credentials=True,
    allow_methods=["*"],    # allow GET, POST, OPTIONS
    allow_headers=["*"],    # allow all headers
)

# --- Data Loading ---
file_path = os.path.join(os.path.dirname(__file__), 'q-vercel-latency.json')

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['latency_ms'] = pd.to_numeric(df['latency_ms'], errors='coerce')
    df['uptime_pct'] = pd.to_numeric(df['uptime_pct'], errors='coerce')
    df.dropna(subset=['latency_ms', 'uptime_pct'], inplace=True)
except Exception as e:
    df = pd.DataFrame(columns=['region', 'latency_ms', 'uptime_pct'])
    print("Error loading JSON:", e)

# --- Request Body Model ---
class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# --- API Endpoint ---
@app.post("/")
async def get_metrics(request_data: MetricsRequest):
    if df.empty:
        # Return empty results instead of 500
        return {region: None for region in request_data.regions}

    results = {}
    for region in request_data.regions:
        region_df = df[df['region'].str.lower() == region.lower()]
        if region_df.empty:
            results[region] = None
            continue

        avg_latency = region_df['latency_ms'].mean()
        p95_latency = np.percentile(region_df['latency_ms'], 95)
        avg_uptime = region_df['uptime_pct'].mean()
        breaches_count = len(region_df[region_df['latency_ms'] > request_data.threshold_ms])

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches_count,
        }

    return results
