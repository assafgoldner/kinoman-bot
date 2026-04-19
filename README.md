# 🎬 קינומן — WhatsApp Movie Identification Bot

בוט WhatsApp שמזהה סרטים מתמונות, תיאורי עלילה או שמות, ומחזיר מידע מלא בעברית.

## מבנה הפרויקט

```
kinoman-bot/
├── .idea/                    # IntelliJ project config
│   └── kinoman-bot.iml
├── src/
│   ├── __init__.py
│   ├── main.py               # Cloud Function entry point
│   ├── claude_client.py      # Claude API integration
│   ├── whatsapp_client.py    # WhatsApp Cloud API integration
│   ├── message_handler.py    # Message routing & session management
│   └── config.py             # Environment variables & constants
├── tests/
│   ├── __init__.py
│   └── test_local.py         # Local testing script
├── prompts/
│   └── system_prompt.txt     # The system prompt (editable separately)
├── .env.example              # Required environment variables
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Quick Start

### 1. Clone & Setup
```bash
cd kinoman-bot
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt   # for local testing
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 3. Test Locally
```bash
python -m tests.test_local
```

### 4. Deploy
```bash
gcloud functions deploy kinoman-bot \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point webhook \
  --source src/ \
  --set-env-vars-file .env \
  --region me-west1 \
  --memory 256MB
```

### 5. Connect Webhook
1. Go to https://developers.facebook.com → Your App → WhatsApp → Configuration
2. Set **Webhook URL** to your Cloud Function URL
3. Set **Verify Token** to match your `VERIFY_TOKEN`
4. Subscribe to **messages** webhook field

## Architecture

```
אבא שולח הודעה/תמונה ב-WhatsApp
        ↓
WhatsApp Cloud API (Meta)
        ↓ POST webhook
Cloud Function (src/main.py)
        ↓
message_handler.py → claude_client.py → Claude API (vision + web_search)
        ↓
whatsapp_client.py → תשובה + כפתורים אינטראקטיביים
        ↓
WhatsApp → חזרה לאבא
```

## Estimated Costs (Family Use)

| Component | Cost |
|-----------|------|
| WhatsApp Cloud API | **Free** (user-initiated, 24h window) |
| Google Cloud Function | **Free** (free tier: 2M invocations/month) |
| Claude API (Sonnet) | **~$0.01-0.05 per query** |
| **Total** | **< $1/month** |

## Customization

- Edit `prompts/system_prompt.txt` to change bot behavior
- The prompt is loaded at startup, no redeploy needed if using a file-based approach
- Add more fuzzy matching logic in `message_handler.py`
