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


def haversine(lat1, lng1, lat2, lng2):
    # Returns distance in km
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_bounding_box(lat, lng, radius_km):
    # Approximate bounding box in degrees
    lat_delta = radius_km / 110.574
    lng_delta = radius_km / (111.320 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - lat_delta,
        "max_lat": lat + lat_delta,
        "min_lng": lng - lng_delta,
        "max_lng": lng + lng_delta,
    }


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


@app.route("/auto-allocation", methods=["GET"])
def get_drivers():
    try:
        pickup_lat = request.args.get("pickup_lat", type=float)
        pickup_lng = request.args.get("pickup_lng", type=float)
        radius_km = request.args.get("radius", default=2, type=float)  # default 2 km

        if pickup_lat is None or pickup_lng is None:
            return jsonify({"error": "pickup_lat and pickup_lng are required"}), 400

        # Get bounding box
        box = get_bounding_box(pickup_lat, pickup_lng, radius_km)

        # Firestore query: range on lat only
        drivers_ref = (
            db.collection("drivers")
            .where("lat", ">=", box["min_lat"])
            .where("lat", "<=", box["max_lat"])
        )

        docs = drivers_ref.stream()

        driver_summaries = []
        for doc in docs:
            data = doc.to_dict()
            driver_lat = data.get("lat")
            driver_lng = data.get("lng")

            if driver_lat is not None and driver_lng is not None:
                # Filter longitude manually
                if box["min_lng"] <= driver_lng <= box["max_lng"]:
                    distance = haversine(driver_lat, driver_lng, pickup_lat, pickup_lng)
                    if distance <= radius_km:
                        driver_summaries.append(
                            {
                                "driver_id": doc.id,
                                "name": data.get("name"),
                                "lat": driver_lat,
                                "lng": driver_lng,
                                "distance_km": round(distance, 2),
                            }
                        )

        # Sort by nearest
        driver_summaries.sort(key=lambda x: x["distance_km"])

        return jsonify({"driver_summaries": driver_summaries}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
