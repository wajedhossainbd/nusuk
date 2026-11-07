# 🕋 Nusuk Master HQ

> **Autonomous Quiz Solver, Referral Keys Manager & Real-Time Orchestrator for the Nusuk Umrah Challenge.**  
> Powered by an offline 377+ verified Islamic Q&A knowledge base, Google Gemini AI, and live cloud synchronization with [nusukkeys.wajed.bd](https://nusukkeys.wajed.bd).

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![ADB Supported](https://img.shields.io/badge/ADB-Android%205.0%2B-green.svg)](https://developer.android.com/studio/command-line/adb)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%202.0-orange.svg)](https://aistudio.google.com/)
[![Keys Cloud Vault](https://img.shields.io/badge/Cloud%20Vault-nusukkeys.wajed.bd-amber.svg)](https://nusukkeys.wajed.bd)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Highlights

* **🧠 100% Accurate Instant Solving**: Built-in 377+ question & answer knowledge base (`quiz_knowledge_base.json`). Solves trivia questions in sub-seconds without guesswork.
* **🤖 Google Gemini AI Engine**: When an unseen question appears, Gemini AI resolves it in real time and automatically stores it in the local database.
* **🔑 Cloud Key Vault Synchronization**: Connects directly to the live cloud database at **[https://nusukkeys.wajed.bd](https://nusukkeys.wajed.bd)**. One click on **Web Sync** pulls over **82,000+ verified referral codes** without keeping heavy databases in git.
* **🛡️ Built-in Anti-Ban Human Simulation**:
  * AMOLED screen auto-dimming (dims brightness to 0 during runs to prevent burn-in and save battery).
  * Natural click jitter (0.8s – 2.5s delay variation).
  * Configurable batch intervals (e.g., 20 questions solved, followed by a 30s breather).
  * Emergency Stop button halts all execution immediately.
* **📱 Universal Android Support**: Works with any Android phone (Samsung, Xiaomi, Pixel, OnePlus, etc.) over standard USB or Wireless ADB (`adb connect <ip>:5555`).
* **👥 Multi-Account Support**: Manage multiple accounts (family & friends) and track individual Umrah draw tickets, win rates, and key balances.

---

## 📋 System Prerequisites

1. **Python 3.8+** (Uses standard library; no complex external pip dependencies required).
2. **Android Debug Bridge (ADB)**:
   * **macOS**: `brew install android-platform-tools`
   * **Ubuntu/Debian**: `sudo apt install adb`
   * **Windows**: Download [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) and add it to your system PATH.
3. **An Android Phone** with the **Nusuk App** installed.

---

## 🚀 Quick Start & Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/wajedhossainbd/nusuk.git
cd nusuk
```

---

### Step 2: Connect Your Android Device

1. On your Android phone, enable **Developer Options**:
   * Open **Settings** $\rightarrow$ **About Phone**.
   * Tap **Build Number** 7 times until you see *"You are now a developer!"*.
2. In **Developer Options**:
   * Enable **USB Debugging**.
   * *(Optional)* Enable **Stay awake** (keeps screen on while charging).
3. Connect your phone to your computer via USB cable.
4. When the pop-up appears on your phone screen, check **"Always allow from this computer"** and tap **Allow**.
5. Test your connection in terminal:
   ```bash
   adb devices
   ```
   You should see your device listed as `device` (e.g., `XXXXXXXX device`).

> 💡 **Wireless ADB (Optional)**: If you prefer running without cables, connect phone and PC to the same Wi-Fi, run `adb tcpip 5555`, unplug the cable, and run `adb connect <your-phone-ip>:5555`.

---

### Step 3: Launch the Master HQ Dashboard

* **On macOS / Linux**:
  ```bash
  ./start.sh
  ```
  *(Or: `python3 dashboard_server.py`)*

* **On Windows**:
  Double-click `start.bat` *(or run `python dashboard_server.py` in Command Prompt)*.

The dashboard will launch automatically in your browser at:
👉 **[http://localhost:5050](http://localhost:5050)**

---

### Step 4: Configure Your Free Google Gemini API Key

1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Sign in with any standard Google account and click **Create API Key** (100% Free).
3. Open your Master HQ Dashboard at `http://localhost:5050`.
4. In the **Google Gemini API** card on the right side:
   * Paste your Gemini API key (starts with `AIzaSy...`).
   * Click **💾 Save Key**.
   * Click **⚡ Test Key** to verify that your connection displays green!

---

### Step 5: Synchronize Verified Referral Keys

1. In the Dashboard, locate the **MASTER KEYS POOL** card.
2. Click the orange **Web Sync** button.
3. The engine will connect to **[https://nusukkeys.wajed.bd](https://nusukkeys.wajed.bd)** and populate your local `nusuk_keys.txt` with verified community keys.

---

### Step 6: Start the Autonomous Loop

1. On your phone, open the **Nusuk app**.
2. Tap the menu $\rightarrow$ **Competitions and challenges** $\rightarrow$ tap **Play now!**.
3. Return to the web dashboard and click **▶ START AUTONOMOUS LOOP**.
4. The system will autonomously:
   * Select challenge doors.
   * Solve Islamic trivia questions instantly.
   * Redeem referral keys whenever your balance gets low.
   * Take human-like breathers between batches.

---

## ⚙️ Configuration Reference (`config.json`)

The dashboard creates and manages `config.json` automatically. You can also edit it directly:

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "device_serial": "",
  "target_keys_topup": 100,
  "min_keys_threshold": 10,
  "questions_per_batch": 20,
  "batch_break_seconds": 30,
  "screen_brightness_dimmed": 0,
  "screen_brightness_normal": 60
}
```

* `device_serial`: Leave empty `""` to auto-detect any connected device, or specify a serial (e.g. `192.168.1.50:5555`).
* `questions_per_batch`: Number of questions to answer before taking a breather.
* `batch_break_seconds`: Rest duration (seconds) between quiz batches.
* `min_keys_threshold`: When your key balance falls below this number, the engine automatically pauses quizzes to redeem keys from the master pool.

---

## 🛠️ Project Structure

```text
├── dashboard_server.py      # Master Web Server (Port 5050)
├── dashboard.html           # Real-Time Cyber Dark UI & Log Console
├── nusuk_engine.py          # Core ADB Orchestrator & Quiz Engine
├── update_nusuk_keys.py     # Live Cloud Vault Synchronizer
├── quiz_knowledge_base.json # 377+ Verified Nusuk Q&A Pairs
├── config.example.json      # Sample Configuration Template
├── accounts.example.json    # Sample Accounts Template
├── start.sh                 # One-Click Launcher (macOS/Linux)
├── start.bat                # One-Click Launcher (Windows)
├── requirements.txt         # Environment Specification
└── README.md                # Project Documentation & Guide
```

---

## ❓ Troubleshooting & FAQ

#### 1. "No device connected (check USB/ADB)"
* Unplug and reconnect the USB cable.
* Check your phone's notification shade and ensure USB mode is set to **File Transfer / MTP** (not "Charge Only").
* Look at your phone screen for the **"Allow USB Debugging?"** prompt and tap **Allow**.
* Run `adb devices` in terminal to confirm your phone displays `device`.

#### 2. "Gemini API Quota / Rate Limit"
* Google AI Studio free tier allows up to 15 requests per minute.
* Because the system ships with **377+ verified questions in `quiz_knowledge_base.json`**, over 95% of questions are answered offline instantly without consuming any Gemini API quota!
* Gemini is only invoked for rare, brand-new questions. Once answered, they are permanently stored in your local knowledge base.

#### 3. "Screen brightness stays dark after stopping"
* Click the **☀️ Normal Brightness** button in the dashboard header to immediately restore standard brightness.

---

## 📄 License & Disclaimer

* **Disclaimer**: This is an independent automation and educational research tool. It is not affiliated with, endorsed by, or associated with the official Nusuk application or the Saudi Ministry of Hajj and Umrah.
* **License**: MIT License. See [LICENSE](LICENSE) for details.
