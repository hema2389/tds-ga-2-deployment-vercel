from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class TelemetryRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# Example telemetry data
telemetry_data = {
    "apac": {"latencies": [170, 180, 200], "uptime": [1, 1, 0]},
    "emea": {"latencies": [160, 175, 190], "uptime": [1, 1, 1]},
}

@app.post("/")
async def check_latency(req: TelemetryRequest):
    response = {}
    for region in req.regions:
        region_data = telemetry_data.get(region, {"latencies": [], "uptime": []})
        latencies = np.array(region_data["latencies"])
        uptimes = np.array(region_data["uptime"])
        threshold = req.threshold_ms
        response[region] = {
            "avg_latency": float(latencies.mean()) if len(latencies) else None,
            "p95_latency": float(np.percentile(latencies, 95)) if len(latencies) else None,
            "avg_uptime": float(uptimes.mean()) if len(uptimes) else None,
            "breaches": int((latencies > threshold).sum())
        }
    return response
