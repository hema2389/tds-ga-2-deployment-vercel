import pandas as pd
import numpy as np
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os

# --- Data Loading ---
# In a real Vercel deployment, you would typically read the data from 
# a database or cloud storage. For this exercise, we load the provided JSON 
# file, assuming it's placed in the root of the deployment bundle.
try:
    # Construct the path to the uploaded file. Vercel bundles files 
    # based on the vercel.json configuration.
    file_path = os.path.join(os.path.dirname(__file__), '..', 'q-vercel-latency.json')
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
    # Ensure latency is numeric and handle case for breaches calculation
    df['latency_ms'] = pd.to_numeric(df['latency_ms'], errors='coerce')
    df.dropna(subset=['latency_ms'], inplace=True)
    
except FileNotFoundError:
    # Fallback/Error state for the data frame
    df = pd.DataFrame(columns=['region', 'latency_ms', 'uptime_pct'])

# --- FastAPI Setup ---
app = FastAPI()

# Enable CORS for POST requests from any origin
# The requirement is to allow POST from any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["POST"], # Allows only POST
    allow_headers=["*"],
)

# --- Request Body Model ---
class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# --- API Endpoint ---
# The route path should match the Vercel routing configuration.
@app.post("/metrics")
async def get_metrics(request_data: MetricsRequest):
    if df.empty:
        raise HTTPException(status_code=500, detail="Telemetry data could not be loaded or is empty.")

    results = {}
    
    for region in request_data.regions:
        region_df = df[df['region'].str.lower() == region.lower()]
        
        if region_df.empty:
            continue

        # 1. avg_latency (mean)
        avg_latency = region_df['latency_ms'].mean()
        
        # 2. p95_latency (95th percentile)
        p95_latency = np.percentile(region_df['latency_ms'], 95)
        
        # 3. avg_uptime (mean) - using the provided 'uptime_pct' column
        avg_uptime = region_df['uptime_pct'].mean()
        
        # 4. breaches (count of records above threshold)
        breaches_count = len(region_df[region_df['latency_ms'] > request_data.threshold_ms])
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches_count,
        }
    
    return results
