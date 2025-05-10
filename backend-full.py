from flask import Flask, request, jsonify
import os
import requests
import json
import pandas as pd
from datetime import datetime
from typing import Union
from flask_cors import CORS
app = Flask(__name__)
import time
CORS(app)

def fetch_flight_data(departure_code, arrival_code, date, save=True):
    api_key = "6817d95a4f9e135e76131836"
    url = f"https://api.flightapi.io/onewaytrip/{api_key}/{departure_code}/{arrival_code}/{date}/1/0/0/Economy/USD"
    response = requests.get(url)
    print("API状态码:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        if save:
            filename = f"/tmp/flights_{departure_code}_{arrival_code}_{date}.json"
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        return data
    else:
        return {"error": f"API request failed with status code {response.status_code}"}

def parse_flight_data(data_or_path: Union[str, dict]):
    if isinstance(data_or_path, str):
        with open(data_or_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = data_or_path

    place_map = {p['id']: p['name'] for p in data['places']}
    carrier_map = {c['id']: c['name'] for c in data['carriers']}
    segment_map = {s['id']: s for s in data['segments']}
    leg_map = {l['id']: l for l in data['legs']}

    itineraries = []
    legs = []

    for itinerary in data["itineraries"]:
        leg_id = itinerary["leg_ids"][0]
        leg = leg_map[leg_id]

        segments = [segment_map[seg_id] for seg_id in leg['segment_ids']]

        dep_time = datetime.fromisoformat(segments[0]['departure']).strftime('%Y-%m-%dT%H:%M:00')
        arr_time = datetime.fromisoformat(segments[-1]['arrival']).strftime('%Y-%m-%dT%H:%M:00')

        stops = []
        for seg in segments[:-1]:  # 除了最后一段
            arr_airport = place_map.get(seg['destination_place_id'], 'UNKNOWN')
            stops.append(arr_airport)

        main_segment = segments[0]
        carrier = carrier_map.get(main_segment['marketing_carrier_id'], 'UNKNOWN')

        price = itinerary['pricing_options'][0]['price']['amount']

        itineraries.append({
            "pricing_options": [{"price": {"amount": price}}],
            "stops": stops,
            "carrier": carrier
        })
        legs.append({
            "departure": dep_time,
            "arrival": arr_time
        })

    return {
        "itineraries": itineraries,
        "legs": legs
    }

@app.route('/flights')
def get_flights():
    departure = request.args.get("departure")
    arrival = request.args.get("arrival")
    date = request.args.get("date")
    try:
        fetch_flight_data(departure, arrival, date)
        data = parse_flight_data(f"/tmp/flights_{departure}_{arrival}_{date}.json")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
