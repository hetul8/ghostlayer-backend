# GhostLayer 🛡️

### The AI Privacy Shield & Personal Vault.

[![Download Beta](https://img.shields.io/badge/Download-Beta_v1.0-blue?style=for-the-badge&logo=google-chrome)](https://github.com/hetul8/ghostlayer-backend/releases/latest)

---

### 🔒 Don't let your PII leak into ChatGPT.

**GhostLayer** acts as a local firewall, masking sensitive data (Emails, Phone Numbers, Names) *before* it leaves your browser. Work securely with AI without training models on your personal information.

### ✨ Features

*   **✅ Smart Redaction**: Automatically detects and masks sensitive entities locally.
*   **✅ Visual Scanner**: Real-time privacy shield ensuring your inputs are safe.
*   **✅ Personal Vault**: (Premium) Browse and recover your masked data history from any device.

---

### 🚀 Installation (For Users)

1.  **Download** the latest `GhostLayer-v1.zip` from [Releases](https://github.com/hetul8/ghostlayer-backend/releases/latest).
2.  **Unzip** the file to a folder.
3.  Open Chrome and go to `chrome://extensions`.
4.  Toggle **Developer Mode** (top right).
5.  Click **Load Unpacked** and select your unzipped folder.
6.  Go to ChatGPT and start typing safely! 👻

---

### 🛠️ For Contributors

If you want to run the backend locally or contribute to the project:

**Prerequisites:** Python 3.9+, PostgreSQL (or Render).

```bash
# 1. Clone the repo
git clone https://github.com/hetul8/ghostlayer-backend.git
cd ghostlayer-backend

# 2. Setup Backend
cd pii_masking
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run Server
python -m uvicorn main:app --reload
```

**Architecture:**
*   **Extension**: standard Manifest V3 (Content Script + Background Proxy).
*   **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Microsoft Presidio.
