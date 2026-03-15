"""
Job Monitor Bot - Scrapes LinkedIn, Naukri, Indeed, Foundit
Sends email alert the moment a new job is found.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import hashlib
import random
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import CONFIG
from company_scrapers import scrape_companies

# ─────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────

def init_db():
    conn = sqlite3.connect("jobs.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            job_id   TEXT PRIMARY KEY,
            title    TEXT,
            company  TEXT,
            location TEXT,
            portal   TEXT,
            url      TEXT,
            found_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def is_new_job(job_id):
    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,))
    found = c.fetchone() is None
    conn.close()
    return found

def save_job(job):
    conn = sqlite3.connect("jobs.db")
    conn.execute(
        "INSERT OR IGNORE INTO seen_jobs VALUES (?,?,?,?,?,?,?)",
        (job["id"], job["title"], job["company"],
         job.get("location",""), job["portal"],
         job["url"], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
#  SCRAPERS
# ─────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def make_id(*parts):
    return hashlib.md5("".join(parts).encode()).hexdigest()

def scrape_linkedin(keyword, location="India"):
    jobs = []
    try:
        url = (
            f"https://www.linkedin.com/jobs/search?"
            f"keywords={requests.utils.quote(keyword)}"
            f"&location={requests.utils.quote(location)}"
            f"&f_TPR=r3600&sortBy=DD"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("div", class_="base-card")[:10]:
            try:
                t = card.find("h3", class_="base-search-card__title")
                c = card.find("h4", class_="base-search-card__subtitle")
                l = card.find("span", class_="job-search-card__location")
                a = card.find("a", class_="base-card__full-link")
                if not t or not a: continue
                link = a["href"].split("?")[0]
                jobs.append({"id": make_id(link), "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "LinkedIn", "url": link})
            except: continue
        print(f"  [LinkedIn] {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")
    return jobs

def scrape_naukri(keyword, location="india"):
    jobs = []
    try:
        slug_kw = keyword.lower().replace(" ", "-")
        slug_loc = location.lower().replace(" ", "-")
        url = f"https://www.naukri.com/{slug_kw}-jobs-in-{slug_loc}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in (soup.find_all("article", class_="jobTuple") or
                     soup.find_all("div", {"class": lambda c: c and "jobTuple" in c}))[:10]:
            try:
                t = card.find("a", class_="title")
                c = card.find("a", class_="subTitle")
                l = card.find("li", class_="location")
                if not t: continue
                link = t.get("href", "")
                jobs.append({"id": make_id(t.get_text(strip=True),
                    c.get_text(strip=True) if c else ""),
                    "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "Naukri", "url": link})
            except: continue
        print(f"  [Naukri]   {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Naukri] Error: {e}")
    return jobs

def scrape_indeed(keyword, location="India"):
    jobs = []
    try:
        url = (
            f"https://in.indeed.com/jobs?q={requests.utils.quote(keyword)}"
            f"&l={requests.utils.quote(location)}&fromage=1&sort=date"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("div", class_="job_seen_beacon")[:10]:
            try:
                t = card.find("h2", class_="jobTitle")
                c = card.find("span", class_="companyName")
                l = card.find("div", class_="companyLocation")
                a = card.find("a", class_="jcs-JobTitle")
                if not t: continue
                href = a.get("href","") if a else ""
                link = f"https://in.indeed.com{href}" if href.startswith("/") else href
                jobs.append({"id": make_id(link), "title": t.get_text(strip=True).replace("new","").strip(),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "Indeed", "url": link})
            except: continue
        print(f"  [Indeed]   {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Indeed] Error: {e}")
    return jobs

def scrape_foundit(keyword, location="india"):
    jobs = []
    try:
        url = (
            f"https://www.foundit.in/srp/results?"
            f"query={requests.utils.quote(keyword)}&locations={location}&sort=1"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("div", class_="card-apply-content")[:10]:
            try:
                t = card.find("h3")
                c = card.find("span", class_="company-name")
                a = card.find("a")
                if not t: continue
                href = a.get("href","") if a else ""
                link = f"https://www.foundit.in{href}" if href.startswith("/") else href
                jobs.append({"id": make_id(t.get_text(strip=True),
                    c.get_text(strip=True) if c else ""),
                    "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": location, "portal": "Foundit", "url": link})
            except: continue
        print(f"  [Foundit]  {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Foundit] Error: {e}")
    return jobs

# ─────────────────────────────────────────
#  COVER LETTER (Ollama — Free & Local)
# ─────────────────────────────────────────

def generate_cover_letter(job):
    """
    Uses Ollama running locally on your machine to generate cover letters.
    100% free — no API key needed.

    Ollama must be running: https://ollama.com
    Pull a model first: ollama pull llama3.2
    """
    profile = CONFIG.get("USER_PROFILE", {})
    if not profile:
        return None

    ollama_url   = CONFIG.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = CONFIG.get("OLLAMA_MODEL", "llama3.2")

    prompt = f"""Write a compelling cover letter (120-150 words) for this job.

Applicant: {profile.get('name', 'Applicant')}
Target Role: {profile.get('target_role', '')}
Skills: {', '.join(profile.get('skills', []))}
Experience: {profile.get('experience_years', 0)} years

Job Title: {job['title']}
Company: {job['company']}
Portal: {job['portal']}

Rules:
- Start with a strong hook — NOT "I am writing to apply"
- Mention one specific skill relevant to this role
- Show genuine interest in the company
- End with a confident call to action
- Sound human and natural, not robotic or generic

Return ONLY the cover letter text. No subject line, no extra commentary."""

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model":  ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 400}
            },
            timeout=120   # local LLMs can be slow on first run
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        print(f"  [Ollama]  ✅ Cover letter generated ({len(text)} chars)")
        return text if text else None
    except requests.exceptions.ConnectionError:
        print("  [Ollama]  ⚠️  Cannot connect — is Ollama running?")
        print("            Start it with: ollama serve")
        return None
    except Exception as e:
        print(f"  [Ollama]  ❌ Error: {e}")
        return None

# ─────────────────────────────────────────
#  EMAIL NOTIFICATION
# ─────────────────────────────────────────

PORTAL_COLORS = {
    "LinkedIn": "#0A66C2",
    "Naukri":   "#FF7555",
    "Indeed":   "#2164f3",
    "Foundit":  "#6C47FF",
}

def build_email_html(job, cover_letter=None):
    """Build the HTML body for the job alert email."""
    color = PORTAL_COLORS.get(job["portal"], "#6366f1")

    cover_html = ""
    if cover_letter:
        cover_html = f"""
        <div style="background:#f0f4ff;border-left:4px solid #6366f1;
                    border-radius:8px;padding:16px 20px;margin-top:20px">
          <p style="margin:0 0 8px;font-weight:700;color:#6366f1;font-size:14px">
            📝 AI-Generated Cover Letter Draft
          </p>
          <p style="margin:0;color:#333;line-height:1.8;font-size:14px;
                    white-space:pre-wrap">{cover_letter}</p>
          <p style="margin:10px 0 0;font-size:11px;color:#999">
            ✏️ Personalize this before sending!
          </p>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
      <div style="max-width:580px;margin:30px auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 2px 12px rgba(0,0,0,0.08)">
        <div style="background:{color};padding:24px 28px">
          <p style="margin:0;color:rgba(255,255,255,0.8);font-size:13px">Job Monitor Bot</p>
          <h1 style="margin:4px 0 0;color:#fff;font-size:22px">🚨 New Job Alert!</h1>
        </div>
        <div style="padding:24px 28px">
          <div style="background:#fafafa;border:1px solid #eee;border-radius:10px;padding:20px">
            <h2 style="margin:0 0 12px;color:#1a1a2e;font-size:20px">{job['title']}</h2>
            <table style="border-collapse:collapse;width:100%">
              <tr>
                <td style="padding:5px 0;color:#888;font-size:13px;width:100px">🏭 Company</td>
                <td style="padding:5px 0;color:#333;font-size:14px;font-weight:600">{job['company']}</td>
              </tr>
              <tr>
                <td style="padding:5px 0;color:#888;font-size:13px">📍 Location</td>
                <td style="padding:5px 0;color:#333;font-size:14px">{job.get('location','India')}</td>
              </tr>
              <tr>
                <td style="padding:5px 0;color:#888;font-size:13px">🌐 Portal</td>
                <td style="padding:5px 0">
                  <span style="background:{color}20;color:{color};padding:2px 10px;
                               border-radius:20px;font-size:12px;font-weight:700">{job['portal']}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:5px 0;color:#888;font-size:13px">⏰ Found at</td>
                <td style="padding:5px 0;color:#333;font-size:14px">
                  {datetime.now().strftime('%d %b %Y, %I:%M %p')}
                </td>
              </tr>
            </table>
          </div>
          <a href="{job['url']}"
             style="display:block;text-align:center;margin:20px 0 0;padding:14px;
                    background:{color};color:#fff;text-decoration:none;border-radius:8px;
                    font-weight:700;font-size:16px;letter-spacing:0.3px">
            ⚡ Apply Now — Be Among the First!
          </a>
          {cover_html}
        </div>
        <div style="background:#f9f9f9;padding:14px 28px;border-top:1px solid #eee">
          <p style="margin:0;color:#aaa;font-size:11px;text-align:center">
            Sent by your Job Monitor Bot • Apply ASAP — early applicants get 3× more callbacks
          </p>
        </div>
      </div>
    </body>
    </html>"""


def send_email_brevo(job, html, subject):
    """Send via Brevo HTTP API — works on Railway (pure HTTPS, no SMTP port).

    Gmail addresses cannot be used as Brevo senders due to Gmail's DMARC policy.
    We use Brevo's own verified domain (no-reply@brevo-mail.io) as the sender,
    while still delivering to your Gmail inbox (EMAIL_TO).
    """
    api_key = CONFIG.get("BREVO_API_KEY", "").strip()
    to      = CONFIG.get("EMAIL_TO", "").strip()

    if not api_key:
        print("  [Brevo]  ⚠️  BREVO_API_KEY not set in Railway Variables")
        return False
    if not to:
        print("  [Brevo]  ⚠️  EMAIL_TO not set")
        return False

    # Gmail/Yahoo/freemail domains are blocked by DMARC when used as Brevo sender.
    # Use Brevo's own safe sender domain instead. You still RECEIVE at your Gmail.
    # Use BREVO_SENDER from Railway env vars (set it to your Brevo account login email)
    # That email is already verified by Brevo automatically on all accounts.
    import os as _os
    safe_sender_email = _os.environ.get("BREVO_SENDER", "").strip() or to
    safe_sender_name  = "Job Monitor Bot"

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key":      api_key,
                "Content-Type": "application/json",
            },
            json={
                "sender":      {"name": safe_sender_name, "email": safe_sender_email},
                "to":          [{"email": to}],
                "subject":     subject,
                "htmlContent": html,
                "headers": {
                    "X-Priority": "1",
                    "X-MSMail-Priority": "High",
                    "Importance": "High",
                },
                "tags": ["job-alert"],
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True
        else:
            print(f"  [Brevo]  ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [Brevo]  ❌ Request error: {e}")
        return False


def send_email_smtp(job, html, subject):
    """
    Send via Gmail SMTP.
    Tries port 587 (STARTTLS) first — Railway allows this.
    Falls back to port 465 (SSL) for local use.
    """
    user = CONFIG.get("EMAIL_USER", "").strip()
    pwd  = CONFIG.get("EMAIL_PASS", "").strip()
    to   = CONFIG.get("EMAIL_TO",   "").strip()
    if not user or not pwd or not to:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Job Monitor Bot <{user}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))

    # Try port 587 (STARTTLS) — works on most cloud platforms
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True
    except Exception as e587:
        print(f"  [SMTP]   ⚠️  Port 587 failed: {e587} — trying port 465")

    # Fall back to port 465 (SSL) — works locally
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True
    except Exception as e465:
        print(f"  [SMTP]   ❌ Port 465 also failed: {e465}")
        return False


def send_email_smtp_direct(subject, html):
    """
    Send directly via Gmail SMTP — no third-party service needed.
    Tries port 587 (STARTTLS) first, then 465 (SSL).
    Both work on Railway free tier.
    """
    user = CONFIG.get("EMAIL_USER", "").strip()
    pwd  = CONFIG.get("EMAIL_PASS", "").strip()
    to   = CONFIG.get("EMAIL_TO",   "").strip()
    if not user or not pwd or not to:
        return False, "EMAIL_USER/EMAIL_PASS/EMAIL_TO not configured"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Job Monitor Bot <{user}>"
    msg["To"]      = to
    msg["X-Priority"] = "1"
    msg["Importance"] = "High"
    msg.attach(MIMEText(html, "html"))

    # Port 587 — STARTTLS (works on Railway)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True, "587"
    except Exception as e587:
        pass

    # Port 465 — SSL (works locally)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True, "465"
    except Exception as e465:
        return False, str(e465)


def build_digest_email(new_jobs):
    """Build one email containing all new jobs found in this scan."""
    count  = len(new_jobs)
    portal_colors = {
        "LinkedIn": "#0A66C2", "Naukri": "#FF7555",
        "Indeed": "#2164f3", "Foundit": "#6C47FF",
    }

    cards = ""
    for job in new_jobs:
        color = portal_colors.get(job["portal"], "#6366f1")
        cards += f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px;
                    margin-bottom:14px;background:#fff;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <h3 style="margin:0 0 4px;color:#1a1a2e;font-size:16px">{job['title']}</h3>
              <p style="margin:0;color:#555;font-size:14px">
                🏭 {job['company']} &nbsp;·&nbsp; 📍 {job.get('location','India')}
              </p>
            </div>
            <span style="background:{color}20;color:{color};padding:3px 10px;
                         border-radius:20px;font-size:11px;font-weight:700;
                         white-space:nowrap;margin-left:12px">{job['portal']}</span>
          </div>
          <a href="{job['url']}"
             style="display:inline-block;margin-top:12px;padding:8px 18px;
                    background:{color};color:#fff;text-decoration:none;
                    border-radius:6px;font-size:13px;font-weight:600">
            ⚡ Apply Now
          </a>
        </div>"""

    return f"""<!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
      <div style="max-width:600px;margin:30px auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 2px 12px rgba(0,0,0,0.08)">
        <div style="background:#6366f1;padding:24px 28px">
          <p style="margin:0;color:rgba(255,255,255,0.8);font-size:13px">Job Monitor Bot</p>
          <h1 style="margin:6px 0 0;color:#fff;font-size:22px">
            🚨 {count} New Job{'s' if count > 1 else ''} Found!
          </h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:13px">
            {datetime.now().strftime('%d %b %Y, %I:%M %p')}
          </p>
        </div>
        <div style="padding:24px 28px">
          {cards}
        </div>
        <div style="background:#f9f9f9;padding:14px 28px;border-top:1px solid #eee">
          <p style="margin:0;color:#aaa;font-size:11px;text-align:center">
            Job Monitor Bot · Apply early — first applicants get 3× more callbacks
          </p>
        </div>
      </div>
    </body></html>"""


# ─────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────

def run_once():
    print(f"\n{'='*52}")
    print(f"  🔍 Scan at {datetime.now().strftime('%d %b %Y  %I:%M:%S %p')}")
    print(f"{'='*52}")

    keywords = CONFIG.get("KEYWORDS", ["developer"])
    location = CONFIG.get("LOCATION", "India")
    portals  = CONFIG.get("PORTALS", ["linkedin","naukri","indeed","foundit"])
    all_jobs = []

    scraper_map = {
        "linkedin": scrape_linkedin,
        "naukri":   scrape_naukri,
        "indeed":   scrape_indeed,
        "foundit":  scrape_foundit,
    }

    for kw in keywords:
        print(f"\n📌 '{kw}'")
        for portal in portals:
            if portal in scraper_map:
                all_jobs += scraper_map[portal](kw, location)
                time.sleep(random.uniform(2, 4))

    # ── Company career portals ──
    all_jobs += scrape_companies(keywords)

    # ── Find genuinely new jobs ──
    new_jobs = []
    for job in all_jobs:
        if is_new_job(job["id"]):
            print(f"  🆕 NEW: {job['title']} @ {job['company']} [{job['portal']}]")
            save_job(job)
            new_jobs.append(job)

    print(f"\n  ✅ {len(new_jobs)} new job(s) | {len(all_jobs)} total scanned")

    # ── Send ONE digest email for all new jobs ──
    # This uses 1 email per scan instead of 1 per job — never hits limits.
    if new_jobs:
        subject = f"⚡ {len(new_jobs)} New Job Alert{'s' if len(new_jobs) > 1 else ''} — {datetime.now().strftime('%d %b %Y')}"
        html    = build_digest_email(new_jobs)

        # Try direct Gmail SMTP first (free, no limits)
        ok, detail = send_email_smtp_direct(subject, html)
        if ok:
            print(f"  [Email] ✅ Digest sent via Gmail SMTP (port {detail}) → {len(new_jobs)} jobs")
        else:
            # Fallback to Brevo if SMTP fails
            print(f"  [Email] SMTP failed ({detail}) — trying Brevo...")
            if CONFIG.get("BREVO_API_KEY", "").strip():
                # Build a dummy job for the brevo function signature
                dummy = {"title": subject, "company": "", "portal": "", "url": "", "location": ""}
                if send_email_brevo(dummy, html, subject):
                    print(f"  [Email] ✅ Digest sent via Brevo → {len(new_jobs)} jobs")
                else:
                    print(f"  [Email] ❌ All methods failed — {len(new_jobs)} jobs not emailed")
            else:
                print(f"  [Email] ❌ No fallback configured — set EMAIL_PASS in Railway")

def main():
    print("╔══════════════════════════════════════╗")
    print("║   ⚡  Job Monitor Bot  —  Email Mode  ║")
    print("╚══════════════════════════════════════╝")
    init_db()

    mins = CONFIG.get("CHECK_INTERVAL_MINUTES", 20)
    print(f"  Interval : every {mins} minutes")
    print(f"  Keywords : {CONFIG.get('KEYWORDS', [])}")
    print(f"  Location : {CONFIG.get('LOCATION', 'India')}")
    print(f"  Email to : {CONFIG.get('EMAIL_TO', 'not set')}")
    print()

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")

        next_time = datetime.now().strftime("%I:%M %p")
        print(f"\n  💤 Sleeping {mins} min... (press Ctrl+C to stop)")
        time.sleep(mins * 60)

if __name__ == "__main__":
    main()