import os
import aiosqlite
from aiohttp import web
import requests
from dotenv import load_dotenv
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.core import BotFrameworkAdapterSettings, ConversationState, MemoryStorage
from botbuilder.integration.aiohttp import BotFrameworkHttpAdapter
from botbuilder.schema import Activity
from rundeck_client import RundeckClient

load_dotenv()
MCP_URL = "http://mcp:5000"

DB_FILE = "software.db"
# Example
BOT_ENDPOINT = os.getenv("BOT_ENDPOINT")

# If you later need to send a request:
requests.post(f"{BOT_ENDPOINT}/somepath", json=payload)

# ------------------------------
# DB Initialization
# ------------------------------
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            software TEXT,
            version TEXT,
            sn_sys_id TEXT,
            sn_number TEXT,
            status TEXT
        )""")
        await db.commit()

# ------------------------------
# Bot Implementation
# ------------------------------
class MyBot(ActivityHandler):
    def __init__(self):
        self.is_supervisor_mode = False

    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text.strip().lower()

        if text == "supervisor":
            self.is_supervisor_mode = True
            reply = (
                "🔑 Supervisor mode enabled. Commands:\n"
                "- `approve <id>`: Approve request (ServiceNow → In Progress)\n"
                "- `install <id>`: Trigger installation (Rundeck + SN close)\n"
                "- `reject <id>`: Reject request (ServiceNow → Cancelled)\n"
                "- `exit`: Leave supervisor mode"
            )
            await turn_context.send_activity(reply)
            return

        if text == "exit":
            self.is_supervisor_mode = False
            await turn_context.send_activity("👤 Back to normal user mode.")
            return

        if self.is_supervisor_mode:
            parts = text.split()
            if len(parts) != 2 or not parts[1].isdigit():
                await turn_context.send_activity("⚠️ Usage: approve <id> | install <id> | reject <id>")
                return

            cmd, req_id = parts
            if cmd == "approve":
                async with aiosqlite.connect(DB_FILE) as db:
                    cur = await db.execute("SELECT sn_sys_id FROM requests WHERE id=?", (req_id,))
                    row = await cur.fetchone()
                if not row:
                    await turn_context.send_activity(f"⚠️ Request {req_id} not found.")
                    return
                sys_id = row[0]
                requests.patch(f"{MCP_URL}/sn/ticket/{sys_id}", json={"state": "2"})
                await turn_context.send_activity(f"✅ Request {req_id} approved (SN → In Progress).")
                return

            if cmd == "install":
                async with aiosqlite.connect(DB_FILE) as db:
                    cur = await db.execute("SELECT sn_sys_id, software, version FROM requests WHERE id=?", (req_id,))
                    row = await cur.fetchone()
                if not row:
                    await turn_context.send_activity(f"⚠️ Request {req_id} not found.")
                    return
                sys_id, software, version = row

                # Trigger Rundeck job
                rundeck = RundeckClient()
                job_id = os.getenv("RUNDECK_JOB_ID")
                exec_data = rundeck.run_job(job_id, options={"software": software, "version": version})
                exec_id = exec_data.get("id")
                await turn_context.send_activity(f"⚙️ Installation started for request {req_id} (Rundeck exec {exec_id}).")

                # Poll Rundeck until finished
                status = "running"
                while status in ["running", "queued"]:
                    exec_status = rundeck.get_execution(exec_id)
                    status = exec_status.get("status")

                # Update ServiceNow → Closed
                requests.patch(f"{MCP_URL}/sn/ticket/{sys_id}", json={
                    "state": "7",
                    "close_notes": f"Installation of {software} {version} completed"
                })

                # Update DB
                async with aiosqlite.connect(DB_FILE) as db:
                    await db.execute("UPDATE requests SET status=? WHERE id=?", ("Completed", req_id))
                    await db.commit()

                await turn_context.send_activity(f"🎉 Installation complete for request {req_id} (SN → Closed).")
                return

            if cmd == "reject":
                async with aiosqlite.connect(DB_FILE) as db:
                    cur = await db.execute("SELECT sn_sys_id FROM requests WHERE id=?", (req_id,))
                    row = await cur.fetchone()
                if not row:
                    await turn_context.send_activity(f"⚠️ Request {req_id} not found.")
                    return
                sys_id = row[0]
                requests.patch(f"{MCP_URL}/sn/ticket/{sys_id}", json={"state": "6"})
                await turn_context.send_activity(f"❌ Request {req_id} rejected (SN → Cancelled).")
                return

            await turn_context.send_activity("❓ Unknown supervisor command.")
            return

        # Normal user mode
        await turn_context.send_activity(f"You said: {text}. Type `supervisor` to enter supervisor mode.")

# ------------------------------
# API endpoint for external software requests
# ------------------------------
async def create_request(request):
    data = await request.json()
    user_id = data.get("user_id")
    software = data.get("software")
    version = data.get("version")

    payload = {
        "short_description": f"Install {software} {version} for {user_id}",
        "description": f"Software request from {user_id}",
        "category": "software"
    }
    resp = requests.post(f"{MCP_URL}/sn/ticket", json=payload)
    sn_data = resp.json().get("result", {})

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO requests (user_id, software, version, sn_sys_id, sn_number, status) VALUES (?,?,?,?,?,?)",
                         (user_id, software, version, sn_data.get("sys_id"), sn_data.get("number"), "Requested"))
        await db.commit()

    return web.json_response({"message": "Request created", "servicenow": sn_data})

# ------------------------------
# Main app setup
# ------------------------------
async def main():
    await init_db()

    app = web.Application()
    bot = MyBot()

    # BotFramework adapter
    settings = BotFrameworkAdapterSettings("", "")
    adapter = BotFrameworkHttpAdapter(settings)

    async def messages(req: web.Request) -> web.Response:
        body = await req.json()
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")
        response = await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200 if response is None else response.status)

    async def ping(req: web.Request) -> web.Response:
        return web.Response(text="Bot is running")

    # Routes
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/api/messages", ping)
    app.router.add_post("/api/request", create_request)

    return app

if __name__ == "__main__":
    import asyncio
    web.run_app(asyncio.run(main()), port=3978)
