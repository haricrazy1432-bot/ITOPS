import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from servicenow_client import ServiceNowClient

load_dotenv()
app = Flask(__name__)

sn_client = ServiceNowClient()

@app.route("/sn/ticket", methods=["POST"])
def create_ticket():
    data = request.json
    result = sn_client.create_ticket(
        short_description=data.get("short_description"),
        description=data.get("description")
    )
    return jsonify(result)

@app.route("/sn/ticket/<sys_id>", methods=["PATCH"])
def update_ticket(sys_id):
    fields = request.json
    result = sn_client.update_ticket(sys_id, fields)
    return jsonify(result)

@app.route("/sn/ticket/<sys_id>", methods=["GET"])
def get_ticket(sys_id):
    result = sn_client.get_ticket(sys_id)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
