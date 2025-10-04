import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- Data Loading ---
try:
    # Load the telemetry data using pandas
    df = pd.read_csv("telemetry.csv")
    df['latency_ms'] = pd.to_numeric(df['latency_ms'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.dropna(subset=['latency_ms'], inplace=True)
except FileNotFoundError:
    # Handle case where file is missing (e.g., in serverless environment)
    df = pd.DataFrame(columns=['region', 'latency_ms', 'status'])

# --- FastAPI Setup ---
app = FastAPI(title="eShopCo Latency API")

# Enable CORS for POST requests from any origin
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

# --- Request Body Model ---
class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# --- API Endpoint ---
@app.post("/api/metrics")
async def get_metrics(request_data: MetricsRequest):
    """
    Returns per-region latency and uptime metrics based on a given threshold.
    """
    if df.empty:
        # Placeholder for real-world deployment where data might be fetched from DB
        raise HTTPException(status_code=500, detail="Telemetry data not loaded.")

    results = {}
    
    for region in request_data.regions:
        region_df = df[df['region'] == region.lower()]
        
        if region_df.empty:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0,
                "error": "No data for this region"
            }
            continue

        # Calculate Latency Metrics
        avg_latency = region_df['latency_ms'].mean()
        p95_latency = np.percentile(region_df['latency_ms'], 95)
        
        # Calculate Uptime/Breaches
        total_records = len(region_df)
        breach_records = region_df[region_df['latency_ms'] > request_data.threshold_ms]
        breaches_count = len(breach_records)
        
        # Uptime is defined as the percentage of records *not* failing 
        # the latency check. Assuming 'status' is not the source of truth,
        # but the latency threshold is.
        up_records = total_records - breaches_count
        avg_uptime = (up_records / total_records) * 100 if total_records > 0 else 0.0
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches_count,
        }
    
    return results

# Required for Vercel's Python runtime to find the ASGI app instance
# if the file is named index.py or app.py. Naming the file api/metrics.py
# might require Vercel config, or you ensure the Vercel function path 
# matches the file path (e.g., /api/metrics).
# For Vercel, the main app instance should be named 'app'.
