import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# Build credentials dictionary from environment variables
service_account_info = {
    "type": "service_account",
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY"),  # handle line breaks
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
}

# Initialize Firebase Admin
cred = credentials.Certificate(service_account_info)
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
