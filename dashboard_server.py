#!/usr/bin/env python3
"""
SCRIPT 4: Nusuk Master HQ Web Dashboard & Orchestrator Server
Hosts the real-time web dashboard on port 5050, connects to Samsung Galaxy S9+ over ADB,
coordinates key synchronizer, key redeemer, and quiz solver, and manages the autonomous cycle.
"""

import http.server
import json
import os
import sys
import threading
import urllib.parse
from nusuk_engine import engine
import update_nusuk_keys

PORT = 5050
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_HTML = os.path.join(PROJECT_DIR, "dashboard.html")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if os.path.exists(DASHBOARD_HTML):
                with open(DASHBOARD_HTML, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>Dashboard file missing</h1>")
            return

        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = engine.get_status()
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        elif path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            cfg = engine.get_config()
            self.wfile.write(json.dumps(cfg).encode("utf-8"))
            return

        elif path == "/api/accounts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            accs = engine.get_accounts()
            self.wfile.write(json.dumps(accs).encode("utf-8"))
            return

        elif path == "/api/knowledge_base":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            kb = engine.get_kb()
            self.wfile.write(json.dumps(kb).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if path == "/api/control":
            action = data.get("action", "")
            resp = {"success": True, "action": action}
            
            if action == "start":
                ok, msg = engine.start_loop()
                resp["message"] = msg
            elif action == "stop":
                ok, msg = engine.stop_loop()
                resp["message"] = msg
            elif action == "topup":
                threading.Thread(target=lambda: engine.redeem_keys_for_account(25), daemon=True).start()
                resp["message"] = "Key redemption started in background (+25 target)."
            elif action == "solve_one":
                threading.Thread(target=engine.solve_single_question, daemon=True).start()
                resp["message"] = "Single question solver triggered."
            elif action == "restore_screen":
                cfg = engine.get_config()
                engine.set_brightness(cfg.get("screen_brightness_normal", 61))
                resp["message"] = "Brightness restored."
            elif action == "dim_screen":
                engine.set_brightness(0)
                resp["message"] = "Screen dimmed to 0."
            else:
                resp = {"success": False, "message": f"Unknown action: {action}"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        elif path == "/api/config":
            new_cfg = engine.update_config(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(new_cfg).encode("utf-8"))
            return

        elif path == "/api/config/test_gemini":
            key = data.get("key", "").strip()
            ok, msg = engine.test_gemini_api(key)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": ok, "message": msg}).encode("utf-8"))
            return

        elif path == "/api/accounts/switch":
            email = data.get("email", "").strip()
            ok, acc = engine.switch_account(email)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": ok, "account": acc}).encode("utf-8"))
            return

        elif path == "/api/accounts/add":
            email = data.get("email", "").strip()
            name = data.get("name", "").strip()
            ok, res = engine.add_account(email, name)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": ok, "result": res if ok else str(res)}).encode("utf-8"))
            return

        elif path == "/api/keys/sync_web":
            import importlib
            importlib.reload(update_nusuk_keys)
            new_added, total = update_nusuk_keys.sync_keys()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "new_keys_added": new_added, "total_keys": total}).encode("utf-8"))
            return

        elif path == "/api/keys/paste":
            text = data.get("text", "")
            new_added, total = engine.append_new_keys(text)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "new_keys_added": new_added, "total_keys": total}).encode("utf-8"))
            return

        elif path == "/api/knowledge_base":
            q = data.get("question", "").strip()
            a = data.get("answer", "").strip()
            if q and a:
                engine.save_kb_entry(q, a)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, DashboardHandler)
    engine.log(f"NUSUK DASHBOARD ACTIVE: Open http://localhost:{PORT} in your Mac browser")
    print(f"\n=======================================================")
    print(f"🚀 NUSUK MASTER DASHBOARD IS LIVE!")
    print(f"👉 Local Mac URL:    http://localhost:{PORT}")
    print(f"👉 Network URL:      http://0.0.0.0:{PORT}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
