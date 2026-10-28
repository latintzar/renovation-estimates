# WhatsApp Renovation Agent

Send a Spanish property listing URL via WhatsApp, get back a full renovation
estimate with costs, timeline, ELI5 summary, and AI-generated after-images.

This integration also supports a conversational mode: if you message without a URL,
it will respond as a chat agent (Gemini Flash) and gradually build a lightweight
memory about your preferences over time.

## Architecture

```
WhatsApp User
    |  sends listing URL
    v
Twilio (WhatsApp Sandbox)
    |  POST webhook
    v
FastAPI: POST /api/webhooks/twilio-whatsapp
    |  1. Extract URL from message
    |  2. Scrape URL (reuse scraper.router.scrape_url)
    |  3. Create listing (reuse database.create_listing)
    |  4. Enqueue V5 pipeline (reuse pricing.v2_scheduler.enqueue_v5_run)
    |  5. Save whatsapp_conversations row (status=processing)
    |  6. Reply "Got it! Analysing..."
    v
Pipeline Worker (unchanged)
    |  Runs all 17 V5 stages
    |  Last stage: v5_room_images
    |  -> Completion hook checks for pending WhatsApp conversation
    v
WhatsApp Agent: handle_pipeline_complete()
    |  1. Read ELI5, BOQ, generated images from unified_estimates
    |  2. Format into WhatsApp messages (formatter.py)
    |  3. Send summary text via Twilio
    |  4. Send after-images via Twilio (using image-serving endpoint)
    |  5. Update conversation status to 'delivered'
    v
WhatsApp User receives renovation estimate + images
```

Conversational mode (no URL) happens inside the same webhook:
- The webhook stores the message in `whatsapp_messages`
- Gemini (alias `flash` → gemini-3-flash-preview) generates a reply
- A short rolling `memory_summary` is updated every 5 messages in `whatsapp_user_profiles`

## Setup (5 minutes)

### 1. Create Twilio Account

1. Go to https://www.twilio.com/ and create a free account
2. Free trial gives $15 credit (enough for hundreds of sandbox messages)

### 2. Activate WhatsApp Sandbox

1. In Twilio Console, go to Messaging > Try it out > Send a WhatsApp message
2. You will see a sandbox number (e.g. +1 415 523 8886) and a join code
3. Send the join message from your phone (e.g. "join hungry-cat") to that number

### 3. Set Environment Variables

Add to your `.env.local` (in the project root):

```bash
# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+12025550100

# Public URL for image serving (set this to your ngrok URL)
PUBLIC_BASE_URL=https://your-subdomain.ngrok.io
```

Find your Account SID and Auth Token in the Twilio Console at https://console.twilio.com/

### 4. Expose Your Server Publicly (ngrok)

Twilio needs to reach your FastAPI server. During development, use ngrok:

```bash
# Install ngrok if you haven't: https://ngrok.com/download

# Start ngrok tunnel to your FastAPI server
ngrok http 8000
```

Copy the https URL ngrok gives you (e.g. https://abc123.ngrok-free.app).

### 5. Configure Twilio Webhook

1. In Twilio Console > Messaging > Try it out > Send a WhatsApp message
2. Under "Sandbox Configuration", set:
   - When a message comes in: https://abc123.ngrok-free.app/api/webhooks/twilio-whatsapp
   - HTTP Method: POST
3. Save

### 6. Update PUBLIC_BASE_URL

Set `PUBLIC_BASE_URL` in `.env.local` to the same ngrok URL:

```bash
PUBLIC_BASE_URL=https://abc123.ngrok-free.app
```

### 7. Start the Backend + Worker

```bash
# Terminal 1: FastAPI server
cd lean-mvp/backend
source ../../.env.local && export TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_WHATSAPP_FROM PUBLIC_BASE_URL
uvicorn main:app --reload --port 8000

# Terminal 2: Pipeline worker
cd lean-mvp/backend
source ../../.env.local && export TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_WHATSAPP_FROM PUBLIC_BASE_URL
PIPELINE_STOP_ON_FAILURE=true PIPELINE_WORKER_CLAIM_LIMIT=1 PIPELINE_MAX_INFLIGHT=1 \
  python -m workers.pipeline_worker
```

### 8. Test It

1. From your phone, send a listing URL to the Twilio sandbox number:
   ```
   https://www.idealista.com/inmueble/12345678/
   ```
2. You should get an immediate reply: "Got it! I'm analysing this property now..."
3. After 3-5 minutes, you will receive the renovation estimate + after-images

### 9. Test Conversational Mode (no URL)

Send a normal message (no URL), for example:

```
Estoy buscando piso en Madrid. Presupuesto 350k. Que barrios me recomiendas?
```

The bot will reply immediately and will remember stable preferences over time
(budget band, preferred city, renovation style) in a compact `memory_summary`.

## Files

| File | Purpose |
|------|---------|
| `whatsapp/__init__.py` | Module marker |
| `whatsapp/twilio_client.py` | Send WhatsApp messages via Twilio REST API |
| `whatsapp/formatter.py` | Format pipeline results into WhatsApp messages |
| `whatsapp/agent.py` | Main orchestration (inbound handling + completion delivery) |
| `routes/webhooks.py` | Twilio webhook endpoint + image serving endpoint |

## Database

The `whatsapp_conversations` table tracks each request:

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| phone_number | text | WhatsApp sender (e.g. whatsapp:+12025550101) |
| inbound_message | text | Original message body |
| listing_url | text | Extracted property URL |
| listing_id | bigint | FK to listings table |
| run_id | text | FK to pipeline_runs |
| status | text | received, processing, completed, delivered, or failed |
| result_summary | jsonb | Cached formatted results after delivery |
| error_message | text | Failure reason if status = failed |

Conversational mode uses two additional tables:

### whatsapp_user_profiles

| Column | Type | Description |
|--------|------|-------------|
| phone_number | text (PK) | WhatsApp sender identifier |
| display_name | text | Name from WhatsApp (best-effort) |
| memory_summary | text | Compact preference memory (no sensitive info) |
| message_count | int | Used to update memory periodically |
| last_listing_id | bigint | Last listing this user analysed |

### whatsapp_messages

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| phone_number | text | WhatsApp sender |
| role | text | user / assistant / system |
| message_text | text | Message content |
| listing_id | bigint | Optional listing context |
| model | text | Model used for assistant responses |
| usage | jsonb | Token usage from Gemini (best-effort) |

## Costs

| Item | Cost |
|------|------|
| Twilio Sandbox | Free |
| Twilio Production (per conversation) | ~$0.04 |
| Pipeline run (Gemini tokens) | ~$0.50-1.50 |

## Production Upgrade Path

When ready to go live:

1. Apply for a WhatsApp Business number via Twilio
2. Create message templates for the initial response and results delivery
3. Replace the ngrok URL with your production domain
4. Consider rate limiting on the webhook endpoint
