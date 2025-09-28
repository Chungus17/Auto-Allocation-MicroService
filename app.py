import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import json

app = Flask(__name__)
CORS(app)

# Load the JSON string from env and parse it
firebase_cred_json = os.environ.get("FIREBASE_CREDENTIALS")
cred_dict = json.loads(firebase_cred_json)

# Initialize with parsed credentials
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()


@app.route("/auto-allocation", methods=["POST"])
def generate_auto_allocation():
    data = request.get_json()
    print(data)
    return jsonify({"received": data}), 200


@app.route("/drivers", methods=["GET"])
def get_drivers():
    try:
        drivers_ref = db.collection("drivers")
        docs = drivers_ref.stream()

        drivers = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        return jsonify(drivers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
