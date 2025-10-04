from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import json
from pathlib import Path

app = FastAPI()

# ✅ Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # allow requests from any origin
    allow_methods=["POST"],    # allow POST requests
    allow_headers=["*"],       # allow any headers
)

class TelemetryRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# Load telemetry data
json_path = Path(__file__).parent / "q-vercel-json.json"
with open(json_path) as f:
    telemetry_raw = json.load(f)

# Organize by region
telemetry_data = {}
for record in telemetry_raw:
    region = record["region"]
    if region not in telemetry_data:
        telemetry_data[region] = {"latencies": [], "uptimes": []}
    telemetry_data[region]["latencies"].append(record["latency_ms"])
    telemetry_data[region]["uptimes"].append(record["uptime_pct"])

@app.post("/")
async def check_latency(req: TelemetryRequest):
    response = {}
    for region in req.regions:
        region_data = telemetry_data.get(region, {"latencies": [], "uptimes": []})
        latencies = np.array(region_data["latencies"])
        uptimes = np.array(region_data["uptimes"])
        threshold = req.threshold_ms

        response[region] = {
            "avg_latency": float(latencies.mean()) if len(latencies) else None,
            "p95_latency": float(np.percentile(latencies, 95)) if len(latencies) else None,
            "avg_uptime": float(uptimes.mean()) if len(uptimes) else None,
            "breaches": int((latencies > threshold).sum())
        }
    return response
