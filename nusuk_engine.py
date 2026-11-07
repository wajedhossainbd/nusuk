#!/usr/bin/env python3
import subprocess
import time
import json
import os
import random
import threading
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")
KEYS_FILE = os.path.join(PROJECT_DIR, "nusuk_keys.txt")
ACCOUNTS_FILE = os.path.join(PROJECT_DIR, "accounts.json")
KB_FILE = os.path.join(PROJECT_DIR, "quiz_knowledge_base.json")
STATE_FILE = os.path.join(PROJECT_DIR, "nusuk_orchestrator_state.json")
LOG_FILE = os.path.join(PROJECT_DIR, "nusuk_orchestrator.log")

DOORS = {
    1: ("The Prophet's Biography", 275, 771),
    2: ("The Quran", 805, 771),
    3: ("Makkah and the Grand Mosque", 275, 1403),
    4: ("Madinah and the Prophet’s Mosque", 805, 1403),
}

class NusukEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.loop_thread = None
        self.stop_requested = False
        self.current_action = "IDLE" # IDLE, PLAYING_QUIZ, TOPPING_UP_KEYS, BATCH_BREAK, PAUSED
        self.logs_buffer = []
        self.last_question = ""
        self.last_answer = ""
        self.last_result = ""
        self.batch_count = 0
        self.break_seconds_left = 0
        self.ensure_files()

    def ensure_files(self):
        # 1. Config
        if not os.path.exists(CONFIG_FILE):
            default_cfg = {
                "gemini_api_key": "",
                "target_keys_topup": 100,
                "min_keys_threshold": 10,
                "questions_per_batch": 20,
                "batch_break_seconds": 30,
                "screen_brightness_dimmed": 0,
                "screen_brightness_normal": 60,
                "device_serial": ""
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_cfg, f, indent=2)

        # 2. Accounts
        if not os.path.exists(ACCOUNTS_FILE):
            default_acc = {
                "active_account": "user@example.com",
                "accounts": {
                    "user@example.com": {
                        "email": "user@example.com",
                        "name": "My Nusuk Account",
                        "keys_balance": 0,
                        "keys_redeemed": 0,
                        "last_key_index": 0,
                        "success_keys": [],
                        "failed_keys": [],
                        "questions_answered": 0,
                        "questions_correct": 0,
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "last_active": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                }
            }
            with open(ACCOUNTS_FILE, "w") as f:
                json.dump(default_acc, f, indent=2)

        # 3. Knowledge base
        if not os.path.exists(KB_FILE):
            with open(KB_FILE, "w") as f:
                json.dump({}, f, indent=2)

    def log(self, msg):
        ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{ts} {msg}"
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        with self.lock:
            self.logs_buffer.append(line)
            if len(self.logs_buffer) > 300:
                self.logs_buffer = self.logs_buffer[-300:]

    def get_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def update_config(self, new_cfg):
        cfg = self.get_config()
        cfg.update(new_cfg)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        self.log("Configuration updated.")
        return cfg

    def get_accounts(self):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"active_account": "", "accounts": {}}

    def save_accounts(self, data):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_active_account(self):
        data = self.get_accounts()
        act_id = data.get("active_account", "")
        acc = data.get("accounts", {}).get(act_id)
        if not acc:
            # fallback first account
            accs = list(data.get("accounts", {}).values())
            return accs[0] if accs else None
        return acc

    def switch_account(self, email):
        data = self.get_accounts()
        if email in data.get("accounts", {}):
            data["active_account"] = email
            data["accounts"][email]["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            self.save_accounts(data)
            self.log(f"Switched active account to: {email}")
            return True, data["accounts"][email]
        return False, "Account does not exist"

    def add_account(self, email, name=""):
        email = email.strip()
        if not email or "@" not in email:
            return False, "Invalid email address"
        data = self.get_accounts()
        if email in data.get("accounts", {}):
            return False, "Account already exists"
        data.setdefault("accounts", {})[email] = {
            "email": email,
            "name": name or email.split("@")[0],
            "keys_balance": 0,
            "keys_redeemed": 0,
            "last_key_index": 0, # Starts from 0 to use all keys for this account!
            "success_keys": [],
            "failed_keys": [],
            "questions_answered": 0,
            "questions_correct": 0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_active": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        data["active_account"] = email
        self.save_accounts(data)
        self.log(f"Added and switched to new account: {email}")
        return True, data["accounts"][email]

    def get_kb(self):
        try:
            with open(KB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_kb_entry(self, question, answer):
        kb = self.get_kb()
        kb[question.strip()] = answer.strip()
        with open(KB_FILE, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)
        self.log(f"KB Updated: '{question[:40]}...' -> '{answer}'")

    def count_total_keys_pool(self):
        if not os.path.exists(KEYS_FILE):
            return 0
        try:
            with open(KEYS_FILE, "r") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def append_new_keys(self, raw_text):
        if not os.path.exists(KEYS_FILE):
            existing_upper = set()
            existing_count = 0
        else:
            with open(KEYS_FILE, "r") as f:
                lines = [l.strip() for l in f if l.strip()]
                existing_upper = set(k.upper() for k in lines)
                existing_count = len(lines)

        candidates = [k.strip() for k in raw_text.replace(",", " ").replace(";", " ").split() if k.strip()]
        new_keys = []
        for c in candidates:
            if c.upper() not in existing_upper and len(c) >= 5:
                existing_upper.add(c.upper())
                new_keys.append(c)

        if new_keys:
            with open(KEYS_FILE, "a") as f:
                for k in new_keys:
                    f.write(k + "\n")
            self.log(f"Appended {len(new_keys)} new unique keys to master pool. Total now: {existing_count + len(new_keys)}")
        return len(new_keys), existing_count + len(new_keys)

    # --- ADB UTILITIES ---
    def get_device_serial(self):
        cfg = self.get_config()
        serial = cfg.get("device_serial", "").strip()
        if serial:
            return serial
        # Auto-detect connected ADB device
        try:
            res = subprocess.run("adb devices", shell=True, text=True, capture_output=True)
            lines = res.stdout.strip().splitlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
        except Exception:
            pass
        return ""

    def adb_sh(self, cmd):
        serial = self.get_device_serial()
        if serial:
            full_cmd = f"adb -s {serial} shell \"{cmd}\""
        else:
            full_cmd = f"adb shell \"{cmd}\""
        res = subprocess.run(full_cmd, shell=True, text=True, capture_output=True)
        return res.stdout

    def set_brightness(self, val):
        self.adb_sh(f"settings put system screen_brightness {val}")

    def get_screen_nodes(self):
        self.adb_sh("uiautomator dump /sdcard/orch_dump.xml")
        xml_str = self.adb_sh("cat /sdcard/orch_dump.xml")
        if not xml_str or "<hierarchy" not in xml_str:
            return []
        try:
            root = ET.fromstring(xml_str)
            nodes = []
            for node in root.iter("node"):
                t = node.attrib.get("text", "").strip()
                d = node.attrib.get("content-desc", "").strip()
                b = node.attrib.get("bounds", "").strip()
                c = node.attrib.get("clickable", "").strip()
                cls = node.attrib.get("class", "").strip()
                if t or d or c == "true" or "EditText" in cls:
                    nodes.append({"text": t or d, "bounds": b, "clickable": c, "class": cls})
            return nodes
        except Exception:
            return []

    def parse_bounds(self, bounds_str):
        parts = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
        x1, y1, x2, y2 = map(int, parts)
        return (x1 + x2) // 2, (y1 + y2) // 2

    def force_clear_input(self):
        self.adb_sh("input keyevent 123") # Move to end
        del_seq = " ".join(["67"] * 40)
        self.adb_sh(f"input keyevent {del_seq}")

    # --- GEMINI / SEARCH AI RESOLVER ---
    def test_gemini_api(self, key_to_test=None):
        api_key = (key_to_test or self.get_config().get("gemini_api_key", "")).strip()
        if not api_key:
            return False, "No Gemini API key provided."
        
        models_to_try = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
        last_err = ""
        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = json.dumps({"contents": [{"parts": [{"text": "Reply with 'OK' only."}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return True, f"Connected to {model}! Response: {reply}"
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP Error {e.code}: {err_body[:150]}"
            except Exception as e:
                last_err = f"Error: {str(e)}"

        return False, last_err

    def query_ai_or_search(self, question, options):
        # Filter out any option with empty or whitespace-only text
        clean_options = [o for o in options if o.get("text", "").strip()]
        if not clean_options:
            return None

        cfg = self.get_config()
        raw_keys = cfg.get("gemini_api_key", "").replace("\n", ",").split(",")
        api_keys = [k.strip() for k in raw_keys if k.strip()]
        
        models_pool = [
            "gemini-3.5-flash-lite", 
            "gemini-3.1-flash-lite", 
            "gemini-flash-lite-latest", 
            "gemini-3-flash-preview"
        ]

        opts_str = "\n".join(f"- {o['text'].strip()}" for o in clean_options)
        prompt = (
            f"You are an Islamic scholar participating in the official Nusuk quiz. "
            f"Select the single correct answer from the options for the question.\n\n"
            f"Question: {question}\n\nOptions:\n{opts_str}\n\n"
            f"Answer with ONLY the exact option text from the list above. No explanation, no punctuation."
        )

        # Robust API Loop: If API is rate-limited or busy, WAIT and RETRY! Never guess a random option!
        if api_keys:
            for attempt in range(1, 25):
                if self.stop_requested:
                    return None

                for api_key in api_keys:
                    for model in models_pool:
                        if self.stop_requested:
                            return None
                        try:
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                            with urllib.request.urlopen(req, timeout=9) as resp:
                                data = json.loads(resp.read().decode("utf-8"))
                                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                                self.log(f"  [{model} AI Response]: '{text}'")
                                
                                # 1. Exact match
                                for o in clean_options:
                                    ot = o["text"].strip().lower()
                                    if ot == text.lower():
                                        return o
                                        
                                # 2. Substring match
                                for o in clean_options:
                                    ot = o["text"].strip().lower()
                                    if len(ot) >= 3 and (ot in text.lower() or text.lower() in ot):
                                        return o
                                        
                                # 3. Word overlap match
                                for o in clean_options:
                                    ot_words = set(o["text"].strip().lower().split())
                                    txt_words = set(text.lower().split())
                                    if ot_words & txt_words:
                                        return o
                                        
                        except urllib.error.HTTPError as e:
                            if e.code == 429:
                                pass # Rate limit on this model/key, rotate to next
                            else:
                                pass
                        except Exception as e:
                            pass

                # If all models/keys were temporarily rate-limited, wait and retry!
                self.log(f"  [Free Tier Rate Limit]: Free quotas busy. Pausing 8s before retry (Attempt {attempt}/25)... (Waiting for correct answer)")
                for _ in range(8):
                    if self.stop_requested:
                        return None
                    time.sleep(1)

        # Fallback: Web Search (only if no API key or API completely exhausted)
        try:
            search_query = urllib.parse.quote(f"islam {question}")
            req = urllib.request.Request(f"https://html.duckduckgo.com/html/?q={search_query}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore").lower()
                best_opt = None
                max_count = 0
                for o in clean_options:
                    ot = o["text"].strip().lower()
                    if not ot or len(ot) < 3: continue
                    cnt = html.count(ot)
                    if cnt > max_count:
                        max_count = cnt
                        best_opt = o
                if best_opt and max_count > 0:
                    self.log(f"  [Search Match]: Found '{best_opt['text']}' ({max_count} hits)")
                    return best_opt
        except Exception as e:
            self.log(f"  [Search Error]: {e}")

        return None

    # --- QUIZ LOGIC ---
    def solve_single_question(self):
        kb = self.get_kb()
        nodes = self.get_screen_nodes()
        all_text = " ".join(n["text"] for n in nodes)

        # Guard: Check if accidentally on Keys tab instead of Play tab
        if "Challeng keys" in all_text or "Check the code" in all_text:
            self.log("Detected Keys tab instead of Play tab. Switching to Play tab...")
            self.adb_sh("input tap 108 2100")
            time.sleep(2.0)
            nodes = self.get_screen_nodes()
            all_text = " ".join(n["text"] for n in nodes)

        # If on door screen, pick random door
        if "Choose a door" in all_text or "Start the challenge" in all_text:
            door_id = random.randint(1, 4)
            name, dx, dy = DOORS[door_id]
            self.log(f"Door: Opening [{name}] at ({dx}, {dy})")
            self.adb_sh(f"input tap {dx} {dy}")
            time.sleep(1.2)
            # Confirm modal: "Open the door"
            self.adb_sh("input tap 540 1872")
            time.sleep(2.0)
            nodes = self.get_screen_nodes()

        # Parse question and options
        question = None
        options = []
        ignored_phrases = [
            "Check your answer", "Close sheet", "Close", "Open the door", 
            "Do you want to use your key?", "Play again", "Share & get a chance to win!",
            "Start the challenge", "Choose a door", "Draw time", "This evening",
            "Don’t miss", "X Platform", "Instagram", "Facebook", "TikTok", "@MyNusuk", "@My_Nusuk"
        ]

        for n in nodes:
            t = n["text"].strip()
            b = n["bounds"]
            if not t or not b:
                continue
            if any(ign in t for ign in ignored_phrases):
                continue
            if "Your key can unlock" in t or "Umrah trip" in t:
                continue
            if t.isdigit() and len(t) <= 4:
                # Update current active account keys balance if found
                acc = self.get_active_account()
                if acc:
                    acc_data = self.get_accounts()
                    acc_data["accounts"][acc["email"]]["keys_balance"] = int(t)
                    self.save_accounts(acc_data)
                continue
            if question is None:
                question = t
            else:
                cx, cy = self.parse_bounds(b)
                options.append({"text": t, "x": cx, "y": cy})

        if not question or not options:
            if "Play again" in all_text:
                self.adb_sh("input tap 540 1976")
                time.sleep(1.5)
                return True
            self.log("Waiting for question screen...")
            return False

        self.last_question = question
        self.log(f"Q: '{question}'")

        # 1. Match from KB
        chosen_opt = None
        if question in kb:
            known = kb[question].strip().lower()
            for o in options:
                ot = o["text"].strip().lower()
                if ot and (ot == known or ot in known or known in ot):
                    chosen_opt = o
                    self.log(f"  -> KB Instant Match: '{o['text']}'")
                    break

        # 2. Query Gemini / Search if not in KB
        if not chosen_opt:
            chosen_opt = self.query_ai_or_search(question, options)

        if not chosen_opt:
            self.log("  [Safety Guard]: No verified answer resolved. Will NOT guess or tap randomly. Waiting...")
            return False

        self.log(f"  -> AI Chosen: '{chosen_opt['text']}'")
        self.last_answer = chosen_opt["text"]

        # Tap option with human jitter
        jx = chosen_opt["x"] + random.randint(-15, 15)
        jy = chosen_opt["y"] + random.randint(-5, 5)
        self.adb_sh(f"input tap {jx} {jy}")
        time.sleep(random.uniform(0.5, 0.8))

        # Tap "Check your answer"
        chk_x = 540 + random.randint(-15, 15)
        chk_y = 2079 + random.randint(-5, 5)
        self.adb_sh(f"input tap {chk_x} {chk_y}")
        time.sleep(random.uniform(2.2, 3.2))

        # Check result screen
        res_nodes = self.get_screen_nodes()
        res_text = " ".join(n["text"] for n in res_nodes)
        
        acc_data = self.get_accounts()
        acc = acc_data["accounts"][acc_data["active_account"]]
        acc["questions_answered"] += 1
        acc["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        if "You’ve reached your daily limit" in res_text or "Something Went Wrong" in res_text:
            self.log("🛑 [Nusuk Daily Limit]: Maximum daily limit (~300 entries) reached for this account! Please switch account or continue tomorrow.")
            self.last_result = "Daily Limit Reached 🛑"
            self.stop_requested = True
            self.adb_sh("input tap 540 1993")
            time.sleep(1.5)
            return False

        if "Correct" in res_text:
            self.log("  -> RESULT: Correct! Confirmed Umrah Draw Ticket! ✅")
            acc["questions_correct"] += 1
            if acc["keys_balance"] > 0:
                acc["keys_balance"] -= 1
            self.save_accounts(acc_data)
            self.last_result = "Correct ✅"
            self.save_kb_entry(question, chosen_opt["text"])

            # Tap "Play again"
            time.sleep(random.uniform(0.8, 1.4))
            self.adb_sh("input tap 540 1976")
            time.sleep(random.uniform(1.2, 1.8))
            return True
        else:
            self.log(f"  -> RESULT: Notice: {res_text[:80]}")
            self.last_result = "Notice ⚠️"
            self.save_accounts(acc_data)
            self.adb_sh("input tap 540 1976")
            time.sleep(1.5)
            return False

    # --- KEY REDEEMER FOR ACTIVE ACCOUNT ---
    def redeem_keys_for_account(self, count_to_redeem=25):
        self.current_action = "TOPPING_UP_KEYS"
        acc_data = self.get_accounts()
        active_email = acc_data.get("active_account")
        acc = acc_data["accounts"][active_email]
        
        self.log(f"Starting Key Redemption for account [{active_email}]. Target: {count_to_redeem} keys.")
        
        if not os.path.exists(KEYS_FILE):
            self.log("Error: nusuk_keys.txt not found!")
            return 0

        with open(KEYS_FILE, "r") as f:
            all_keys = [line.strip() for line in f if line.strip()]

        last_idx = acc.get("last_key_index", 0)
        keys_pool = all_keys[last_idx:]
        if not keys_pool:
            self.log(f"No more unused keys left for {active_email} (Index: {last_idx})")
            return 0

        # Switch to Keys Tab (Center: 540, 2100)
        self.adb_sh("input tap 540 2100")
        time.sleep(2.0)

        redeemed_this_session = 0
        current_idx = last_idx

        for key in keys_pool:
            if self.stop_requested or redeemed_this_session >= count_to_redeem:
                break

            current_idx += 1
            self.log(f"[{active_email}] (#{current_idx}/{len(all_keys)}) Redeeming: {key}")

            # 1. Tap code box (540, 1347)
            rx = 540 + random.randint(-20, 20)
            ry = 1347 + random.randint(-10, 10)
            self.adb_sh(f"input tap {rx} {ry}")
            time.sleep(0.4)

            # Clear box
            self.force_clear_input()
            time.sleep(0.3)

            # Type key
            self.adb_sh(f"input text {key}")
            time.sleep(0.3)
            # Dismiss keyboard
            self.adb_sh("input keyevent 111")
            time.sleep(0.5)

            # Tap "Check the code" (540, 1558)
            cx = 540 + random.randint(-20, 20)
            cy = 1558 + random.randint(-5, 5)
            self.adb_sh(f"input tap {cx} {cy}")
            time.sleep(random.uniform(2.4, 3.2))

            # Inspect result
            nodes = self.get_screen_nodes()
            text_dump = " ".join(n["text"] for n in nodes)

            if "Add another code to get a key" in text_dump or "Congratulations" in text_dump or "successfully" in text_dump:
                self.log(f"  -> SUCCESS! Key {key} redeemed! 🔑")
                acc["keys_redeemed"] += 1
                acc["keys_balance"] += 1
                acc["success_keys"].append(key)
                redeemed_this_session += 1
                # Tap "Add another code to get a key" (540, 2118)
                ax = 540 + random.randint(-20, 20)
                ay = 2118 + random.randint(-8, 8)
                self.adb_sh(f"input tap {ax} {ay}")
                time.sleep(random.uniform(1.2, 1.8))
            else:
                self.log(f"  -> Key rejected or invalid: {key}")
                acc["failed_keys"].append(key)
                self.force_clear_input()

            acc["last_key_index"] = current_idx
            acc["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            self.save_accounts(acc_data)
            time.sleep(random.uniform(2.5, 4.5))

        # Switch back to Play Tab (Center: 108, 2100)
        self.adb_sh("input tap 108 2100")
        time.sleep(2.0)
        self.log(f"Key redemption finished. Redeemed {redeemed_this_session} keys. Account balance: {acc['keys_balance']}.")
        return redeemed_this_session

    # --- AUTONOMOUS BATCH LOOP ---
    def start_loop(self):
        if self.loop_thread and self.loop_thread.is_alive():
            return False, "Loop is already running."
        self.stop_requested = False
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        return True, "Loop started."

    def stop_loop(self):
        self.stop_requested = True
        self.current_action = "IDLE"
        self.log("🛑 STOP SIGNAL RECEIVED. Halting all current actions immediately.")
        cfg = self.get_config()
        self.set_brightness(cfg.get("screen_brightness_normal", 61))
        return True, "Execution stopped immediately."

    def _run_loop(self):
        cfg = self.get_config()
        self.log("=== AUTONOMOUS ORCHESTRATION LOOP INITIATED ===")
        
        # Keep macOS awake even if screen is locked
        caffeinate_proc = None
        try:
            caffeinate_proc = subprocess.Popen(["caffeinate", "-dis"])
            self.log("macOS Keep-Awake active (caffeinate). Will run continuously even when locked.")
        except Exception:
            pass

        self.adb_sh("svc power stayon true")
        self.set_brightness(cfg.get("screen_brightness_dimmed", 0))

        try:
            while not self.stop_requested:
                cfg = self.get_config()
                acc_data = self.get_accounts()
                active_email = acc_data.get("active_account", "")
                acc = acc_data["accounts"].get(active_email, {})

                keys_balance = acc.get("keys_balance", 0)
                min_thresh = cfg.get("min_keys_threshold", 10)
                target_topup = cfg.get("target_keys_topup", 100)

                # 1. Top-up Check
                if keys_balance <= min_thresh:
                    needed = max(20, target_topup - keys_balance)
                    self.log(f"Keys balance ({keys_balance}) is at/below {min_thresh}. Initiating top-up for +{needed} keys...")
                    self.redeem_keys_for_account(needed)

                if self.stop_requested:
                    break

                # 2. Run Batch of Questions
                batch_size = cfg.get("questions_per_batch", 20)
                self.current_action = "PLAYING_QUIZ"
                self.log(f"--- Starting batch of {batch_size} questions for {active_email} ---")
                
                for q_i in range(batch_size):
                    if self.stop_requested:
                        break
                    self.batch_count = q_i + 1
                    self.log(f"[Batch {self.batch_count}/{batch_size}] (Account Keys: {acc.get('keys_balance', 0)} | Correct: {acc.get('questions_correct', 0)})")
                    
                    self.solve_single_question()

                    # Refresh account state
                    acc_data = self.get_accounts()
                    acc = acc_data["accounts"].get(active_email, {})
                    if acc.get("keys_balance", 0) <= min_thresh:
                        self.log(f"Keys low ({acc.get('keys_balance', 0)}). Breaking batch for top-up.")
                        break

                    time.sleep(random.uniform(2.5, 4.5))

                if self.stop_requested:
                    break

                # 3. Take Breather Break
                break_duration = cfg.get("batch_break_seconds", 30)
                self.current_action = "BATCH_BREAK"
                self.log(f"--- Batch Complete! Taking a human break for {break_duration}s ---")
                for sec in range(int(break_duration), 0, -1):
                    if self.stop_requested:
                        break
                    self.break_seconds_left = sec
                    time.sleep(1)
                self.break_seconds_left = 0

        finally:
            if caffeinate_proc:
                try:
                    caffeinate_proc.terminate()
                except Exception:
                    pass
            self.current_action = "IDLE"
            self.log("Autonomous loop ended. Screen brightness restored.")
            self.set_brightness(cfg.get("screen_brightness_normal", 61))

    def get_status(self):
        acc_data = self.get_accounts()
        active_email = acc_data.get("active_account", "")
        active_acc = acc_data.get("accounts", {}).get(active_email, {})
        cfg = self.get_config()
        
        has_gemini = bool(cfg.get("gemini_api_key", "").strip())
        is_running = self.loop_thread is not None and self.loop_thread.is_alive()

        return {
            "status": self.current_action if is_running else "IDLE",
            "is_running": is_running,
            "active_account": active_email,
            "account_info": active_acc,
            "all_accounts": acc_data.get("accounts", {}),
            "keys_pool_total": self.count_total_keys_pool(),
            "batch_count": self.batch_count,
            "questions_per_batch": cfg.get("questions_per_batch", 20),
            "break_seconds_left": self.break_seconds_left,
            "last_question": self.last_question,
            "last_answer": self.last_answer,
            "last_result": self.last_result,
            "has_gemini_key": has_gemini,
            "gemini_masked_key": f"AIzaSy...{cfg.get('gemini_api_key', '')[-4:]}" if has_gemini and len(cfg.get('gemini_api_key', '')) > 8 else ("Configured" if has_gemini else "Not Configured"),
            "device_serial": self.get_device_serial() or "No device connected (check USB/ADB)",
            "kb_total_questions": len(self.get_kb()),
            "logs": self.logs_buffer[-50:]
        }

engine = NusukEngine()
