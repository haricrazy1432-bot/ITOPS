import os
import requests
from dotenv import load_dotenv

load_dotenv()

RUNDECK_URL = os.getenv("RUNDECK_URL")
RUNDECK_TOKEN = os.getenv("RUNDECK_TOKEN")
HEADERS = {"X-Rundeck-Auth-Token": RUNDECK_TOKEN, "Content-Type": "application/json"}

class RundeckClient:
    def __init__(self, base_url=RUNDECK_URL):
        self.base_url = base_url.rstrip("/")

    def run_job(self, job_id, options=None):
        url = f"{self.base_url}/api/41/job/{job_id}/run"
        resp = requests.post(url, headers=HEADERS, json={"options": options or {}})
        resp.raise_for_status()
        return resp.json()

    def get_execution(self, exec_id):
        url = f"{self.base_url}/api/41/execution/{exec_id}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
