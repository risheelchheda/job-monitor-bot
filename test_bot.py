"""
test_bot.py — Run this FIRST to verify everything is working.
"""

import smtplib
import requests
from datetime import datetime
from config import CONFIG

print("╔══════════════════════════════════╗")
print("║   Job Monitor Bot — Setup Test   ║")
print("╚══════════════════════════════════╝\n")

# ── 1. Gmail ──────────────────────────────────────────────────────────
print("1️⃣  Testing Gmail login...")
user = CONFIG.get("EMAIL_USER", "").strip()
pwd  = CONFIG.get("EMAIL_PASS", "").strip()
to   = CONFIG.get("EMAIL_TO",   "").strip()

if not user or not pwd:
    print("   ⏭️  Skipped — fill EMAIL_USER and EMAIL_PASS in config.py\n")
else:
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pwd)
        print("   ✅ Gmail login successful!")

        # Send a test email
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ Job Monitor Bot — Setup Confirmed!"
        msg["From"]    = f"Job Monitor Bot <{user}>"
        msg["To"]      = to or user
        msg.attach(MIMEText(f"""
        <div style="font-family:Arial;max-width:520px;margin:20px auto;
                    background:#f0f4ff;padding:24px;border-radius:12px">
          <h2 style="color:#6366f1">✅ Job Monitor Bot is working!</h2>
          <p style="color:#333">
            You will receive an email like this every time a new job matching
            your keywords appears on LinkedIn, Naukri, Indeed, or Foundit.
          </p>
          <p style="color:#555;font-size:13px">
            🤖 Cover letters powered by Ollama (free, local AI)<br>
            📍 Location: {CONFIG.get('LOCATION','India')}<br>
            🔍 Keywords: {', '.join(CONFIG.get('KEYWORDS', []))}<br>
            ⏱️  Checking every: {CONFIG.get('CHECK_INTERVAL_MINUTES', 20)} minutes
          </p>
        </div>""", "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pwd)
            s.sendmail(user, to or user, msg.as_string())
        print(f"   📧 Test email sent to {to or user} — check your inbox!\n")

    except smtplib.SMTPAuthenticationError:
        print("   ❌ Login FAILED.")
        print("   💡 Common fixes:")
        print("      • Use an App Password, NOT your real Gmail password")
        print("      • App Password must have NO spaces (16 chars)")
        print("      • Make sure 2-Step Verification is ON in Google account\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")


# ── 2. Ollama ─────────────────────────────────────────────────────────
print("2️⃣  Testing Ollama (local AI)...")
ollama_url   = CONFIG.get("OLLAMA_URL",   "http://localhost:11434")
ollama_model = CONFIG.get("OLLAMA_MODEL", "llama3.2")

try:
    # Check if Ollama is running
    resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
    resp.raise_for_status()
    available = [m["name"] for m in resp.json().get("models", [])]

    if not available:
        print("   ⚠️  Ollama is running but NO models are installed.")
        print(f"   👉 Run this in your terminal:  ollama pull {ollama_model}\n")
    else:
        print(f"   ✅ Ollama is running!")
        print(f"   📦 Models installed: {', '.join(available)}")

        # Check if configured model is available
        model_short = ollama_model.split(":")[0]
        if any(model_short in m for m in available):
            print(f"   ✅ Model '{ollama_model}' is ready!")

            # Quick generation test
            print(f"   🧪 Testing generation with '{ollama_model}'...")
            test = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": ollama_model, "prompt": "Say 'Ollama OK' only.",
                      "stream": False, "options": {"num_predict": 10}},
                timeout=60
            )
            result = test.json().get("response", "").strip()
            print(f"   ✅ Generation works — response: '{result}'\n")
        else:
            print(f"   ⚠️  Model '{ollama_model}' not found in installed models.")
            print(f"   👉 Run:  ollama pull {ollama_model}\n")
            print(f"   Available models: {', '.join(available)}\n")

except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to Ollama.")
    print("   💡 Fix:")
    print("      1. Download Ollama from https://ollama.com/download")
    print("      2. Install and open it")
    print(f"     3. Run in terminal:  ollama pull {ollama_model}")
    print("      4. Then run:         ollama serve")
    print("      5. Re-run this test\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")


# ── 3. Scraper test ───────────────────────────────────────────────────
print("3️⃣  Testing scrapers (quick check)...")
from job_monitor import scrape_linkedin, scrape_naukri

kw  = CONFIG["KEYWORDS"][0] if CONFIG.get("KEYWORDS") else "developer"
loc = CONFIG.get("LOCATION", "India")

j1 = scrape_linkedin(kw, loc)
j2 = scrape_naukri(kw, loc)
total = len(j1) + len(j2)

if total > 0:
    print(f"   ✅ Scrapers working — {total} jobs found for '{kw}'")
    print(f"   Sample: {j1[0]['title']} @ {j1[0]['company']}" if j1 else "")
else:
    print(f"   ⚠️  0 jobs found — LinkedIn/Naukri may be rate-limiting.")
    print("   This is normal. The bot will still work — try again in 5 min.")

print("\n" + "─"*42)
print("🎉 Test complete!")
print()
print("   Next steps:")
print("   1. If email ✅ and Ollama ✅ → run: python job_monitor.py")
print("   2. For 24/7 hosting → read DEPLOY.md")
print()
print("   ⚠️  IMPORTANT for 24/7 cloud hosting (Railway/PythonAnywhere):")
print("      Ollama runs LOCALLY on your computer only.")
print("      On the cloud, cover letters will be skipped (bot still works!")
print("      For cloud cover letters, set GENERATE_COVER_LETTERS: False in config.py")