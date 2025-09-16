import os
import requests
from dotenv import load_dotenv

load_dotenv()

class ServiceNowClient:
    def __init__(self):
        self.instance = os.getenv("SERVICENOW_INSTANCE")
        self.user = os.getenv("SERVICENOW_USER")
        self.password = os.getenv("SERVICENOW_PASS")
        self.base_url = f"{self.instance}/api/now/table/incident"
        self.auth = (self.user, self.password)
        self.headers = {"Content-Type": "application/json"}

    def create_ticket(self, short_description, description):
        data = {
            "short_description": short_description,
            "description": description,
            "category": "software"
        }
        resp = requests.post(self.base_url, auth=self.auth, headers=self.headers, json=data)
        return resp.json()

    def update_ticket(self, sys_id, fields):
        url = f"{self.base_url}/{sys_id}"
        resp = requests.patch(url, auth=self.auth, headers=self.headers, json=fields)
        return resp.json()

    def get_ticket(self, sys_id):
        url = f"{self.base_url}/{sys_id}"
        resp = requests.get(url, auth=self.auth, headers=self.headers)
        return resp.json()
