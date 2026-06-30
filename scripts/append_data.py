import json
import os
from datetime import datetime, timezone
import requests

DATA_FILE = "data/hourly_weather_append.json"
LATITUDE = 51.5
LONGITUDE = -0.0

# 1. Load existing data (handle first-run case where file doesn't exist yet)
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        existing_data = json.load(f)
else:
    existing_data = []

# 2. Work out the start date — day after the last entry we have, or a sensible default
if existing_data:
    last_datetime = max(entry["datetime"] for entry in existing_data)
    start_date = last_datetime[:10]  # just the date part, re-fetch that day to catch any gaps
else:
    start_date = "2026-06-29"  # fallback for first ever run

end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # always "today", never hardcoded

# 3. Fetch from Open-Meteo
params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "hourly": "temperature_2m",
    "start_date": start_date,
    "end_date": end_date,
    "timezone": "auto"
}

response = requests.get("https://api.open-meteo.com/v1/forecast", params=params)
response.raise_for_status()
result = response.json()

times = result["hourly"]["time"]
temps = result["hourly"]["temperature_2m"]

# 4. Build new entries, skipping nulls and anything beyond the current hour (i.e. forecast)
now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

new_entries = [
    {"datetime": t, "temp": temp}
    for t, temp in zip(times, temps)
    if temp is not None and t <= now_utc
]

# 5. Merge, de-duplicating by datetime (existing entries take priority over re-fetched ones)
combined = {entry["datetime"]: entry for entry in new_entries}
combined.update({entry["datetime"]: entry for entry in existing_data})
merged = sorted(combined.values(), key=lambda e: e["datetime"])

# 6. Write back
with open(DATA_FILE, "w") as f:
    json.dump(merged, f, indent=2)

print(f"Data file now has {len(merged)} entries, spanning {merged[0]['datetime']} to {merged[-1]['datetime']}")
