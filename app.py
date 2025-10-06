import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from google.cloud.firestore_v1 import GeoPoint
from google.protobuf.timestamp_pb2 import Timestamp as ProtoTimestamp
import datetime
from geopy.distance import geodesic
import math

app = Flask(__name__)
CORS(app)

# Load credentials from env
firebase_cred_json = os.environ.get("FIREBASE_CREDENTIALS")
cred_dict = json.loads(firebase_cred_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()


def get_bounding_box(lat, lng, radius_km):
    # Approximate bounding box: 1 degree ≈ 111 km
    delta = radius_km / 111.0
    return {
        "min_lat": lat - delta,
        "max_lat": lat + delta,
        "min_lng": lng - delta,
        "max_lng": lng + delta,
    }


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def calculate_distance(driver_lat, driver_lng, pickup_lat, pickup_lng):
    """Returns distance in km between driver and pickup location."""
    return geodesic((driver_lat, driver_lng), (pickup_lat, pickup_lng)).km


# Recursive serializer for Firestore types
def serialize_firestore(obj):
    if isinstance(obj, GeoPoint):
        return {"lat": obj.latitude, "lng": obj.longitude}
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_firestore(i) for i in obj]
    if isinstance(obj, dict):
        return {k: serialize_firestore(v) for k, v in obj.items()}
    if isinstance(obj, ProtoTimestamp):
        return obj.ToDatetime().isoformat()
    return obj


# @app.route("/auto-allocation", methods=["GET"])
# def get_drivers():
#     try:
#         # Get pickup coordinates from query parameters
#         pickup_lat = request.args.get("pickup_lat", type=float)
#         pickup_lng = request.args.get("pickup_lng", type=float)

#         if pickup_lat is None or pickup_lng is None:
#             return jsonify({"error": "pickup_lat and pickup_lng are required"}), 400

#         drivers_ref = db.collection("drivers")
#         docs = drivers_ref.stream()

#         full_drivers = []
#         driver_summaries = []

#         for doc in docs:
#             data = doc.to_dict()
#             clean_data = serialize_firestore(data)
#             clean_data["id"] = doc.id
#             full_drivers.append(clean_data)

#             # Extract summary fields
#             driver_lat = clean_data.get("lat") or clean_data.get("location", {}).get(
#                 "lat"
#             )
#             driver_lng = clean_data.get("lng") or clean_data.get("location", {}).get(
#                 "lng"
#             )

#             if driver_lat is not None and driver_lng is not None:
#                 distance_km = calculate_distance(
#                     driver_lat, driver_lng, pickup_lat, pickup_lng
#                 )
#                 driver_summary = {
#                     "driver_id": clean_data.get("driver_id") or clean_data.get("id"),
#                     "name": clean_data.get("name"),
#                     "lat": driver_lat,
#                     "lng": driver_lng,
#                     "distance_km": round(distance_km, 2),
#                 }
#                 driver_summaries.append(driver_summary)

#         # Optionally, sort summaries by nearest driver
#         driver_summaries.sort(key=lambda x: x["distance_km"])

#         return (
#             jsonify({"driver_summaries": driver_summaries}),
#             200,
#         )

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route("/auto-allocation", methods=["GET"])
def get_drivers():
    try:
        pickup_lat = request.args.get("pickup_lat", type=float)
        pickup_lng = request.args.get("pickup_lng", type=float)
        radius_km = request.args.get("radius", type=int)

        if pickup_lat is None or pickup_lng is None:
            return jsonify({"error": "pickup_lat and pickup_lng are required"}), 400

        # Get bounding box for 2 km radius
        box = get_bounding_box(pickup_lat, pickup_lng, radius_km)

        # Query Firestore for drivers in bounding box
        drivers_ref = (
            db.collection("drivers")
            .where("lat", ">=", box["min_lat"])
            .where("lat", "<=", box["max_lat"])
            .where("lng", ">=", box["min_lng"])
            .where("lng", "<=", box["max_lng"])
        )

        docs = drivers_ref.stream()

        driver_summaries = []
        for doc in docs:
            data = doc.to_dict()
            driver_lat = data.get("location", {}).get("lat")
            driver_lng = data.get("location", {}).get("lng")

            if driver_lat is not None and driver_lng is not None:
                distance_km = haversine(driver_lat, driver_lng, pickup_lat, pickup_lng)

                # Only keep drivers within 2 km radius
                if distance_km <= 2:
                    driver_summaries.append(
                        {
                            "driver_id": data.get("driver_id") or doc.id,
                            "name": data.get("name"),
                            "lat": driver_lat,
                            "lng": driver_lng,
                            "distance_km": round(distance_km, 2),
                        }
                    )

        # Sort by nearest first
        driver_summaries.sort(key=lambda x: x["distance_km"])

        return jsonify({"driver_summaries": driver_summaries}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
