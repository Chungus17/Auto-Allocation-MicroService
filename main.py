import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/auto-allocation", methods=["POST"])  
def generate_auto_allocation():
    data = request.get_json()  
    print(data)  
    return jsonify({"received": data}), 200  


if __name__ == "__main__":
    app.run(debug=True)  
