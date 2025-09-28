import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from google.cloud.firestore_v1 import GeoPoint
from google.protobuf.timestamp_pb2 import Timestamp as ProtoTimestamp
import datetime

app = Flask(__name__)
CORS(app)

# Load credentials from env
firebase_cred_json = os.environ.get("FIREBASE_CREDENTIALS")
cred_dict = json.loads(firebase_cred_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()


@app.route("/auto-allocation", methods=["POST"])
def generate_auto_allocation():
    data = request.get_json()
    print(data)
    return jsonify({"received": data}), 200


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


@app.route("/drivers", methods=["GET"])
def get_drivers():
    try:
        drivers_ref = db.collection("drivers")
        docs = drivers_ref.stream()
        drivers = []

        for doc in docs:
            data = doc.to_dict()
            clean_data = serialize_firestore(data)
            clean_data["id"] = doc.id
            drivers.append(clean_data)

        return jsonify(drivers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
