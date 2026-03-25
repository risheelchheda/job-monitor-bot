"""
job_monitor.py  —  AWS Lambda version

KEY CHANGES vs Railway version:
  1. lambda_handler(event, context) replaces main() + while True loop
     EventBridge calls lambda_handler every 20 min — no sleep() needed.

  2. SQLite DB lives at /tmp/jobs.db
     Lambda gives you a writable /tmp (512 MB).
     IMPORTANT: /tmp is ephemeral — it persists only within the same
     Lambda container instance (warm invocations). A cold start gets a
     fresh /tmp, meaning the bot may re-alert old jobs.
     ✅ For production-grade dedup, replace SQLite with DynamoDB (see
        the comment block near init_db()). For personal use SQLite in
        /tmp is fine since most warm invocations reuse the same container.

  3. Brevo removed — email is sent via Gmail SMTP only (port 587 / 465).
     Lambda does NOT block outbound SMTP like Railway did, so direct
     Gmail SMTP works reliably here.

  4. time.sleep() calls between scrapers are kept short (1–2 s) to stay
     within Lambda's 15-minute timeout. Total scan time is ~5–8 minutes
     for this many companies.

  5. No cover letter generation — Ollama is local-only.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import hashlib
import random
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import CONFIG
from company_scrapers import scrape_companies

# ─────────────────────────────────────────
#  DATABASE  (SQLite in Lambda /tmp)
# ─────────────────────────────────────────
# Lambda's /tmp is writable and persists across warm invocations of the
# SAME container. Cold starts get a fresh /tmp (no history).
#
# 💡 Want true persistence across cold starts?
#    Replace the three functions below with DynamoDB calls:
#
#    import boto3
#    _ddb  = boto3.resource("dynamodb", region_name="ap-south-1")
#    _table = _ddb.Table("job_monitor_seen")
#
#    def is_new_job(job_id):
#        resp = _table.get_item(Key={"job_id": job_id})
#        return "Item" not in resp
#
#    def save_job(job):
#        _table.put_item(Item={
#            "job_id":   job["id"],
#            "title":    job["title"],
#            "company":  job["company"],
#            "location": job.get("location", ""),
#            "portal":   job["portal"],
#            "url":      job["url"],
#            "found_at": datetime.now().isoformat(),
#        })
# ─────────────────────────────────────────

DB_PATH = "/tmp/jobs.db"   # ← Lambda writable temp storage


def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,))
    found = c.fetchone() is None
    conn.close()
    return found


def save_job(job):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO seen_jobs VALUES (?,?,?,?,?,?,?)",
        (job["id"], job["title"], job["company"],
         job.get("location", ""), job["portal"],
         job["url"], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
#  SCRAPERS  (unchanged from Railway)
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
                if not t or not a:
                    continue
                link = a["href"].split("?")[0]
                jobs.append({
                    "id": make_id(link),
                    "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "LinkedIn", "url": link,
                })
            except:
                continue
        print(f"  [LinkedIn] {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")
    return jobs


def scrape_naukri(keyword, location="india"):
    jobs = []
    try:
        slug_kw  = keyword.lower().replace(" ", "-")
        slug_loc = location.lower().replace(" ", "-")
        url = f"https://www.naukri.com/{slug_kw}-jobs-in-{slug_loc}"
        r   = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in (soup.find_all("article", class_="jobTuple") or
                     soup.find_all("div", {"class": lambda c: c and "jobTuple" in c}))[:10]:
            try:
                t = card.find("a", class_="title")
                c = card.find("a", class_="subTitle")
                l = card.find("li", class_="location")
                if not t:
                    continue
                link = t.get("href", "")
                jobs.append({
                    "id": make_id(t.get_text(strip=True),
                                  c.get_text(strip=True) if c else ""),
                    "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "Naukri", "url": link,
                })
            except:
                continue
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
                if not t:
                    continue
                href = a.get("href", "") if a else ""
                link = f"https://in.indeed.com{href}" if href.startswith("/") else href
                jobs.append({
                    "id": make_id(link),
                    "title": t.get_text(strip=True).replace("new", "").strip(),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal": "Indeed", "url": link,
                })
            except:
                continue
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
                if not t:
                    continue
                href = a.get("href", "") if a else ""
                link = f"https://www.foundit.in{href}" if href.startswith("/") else href
                jobs.append({
                    "id": make_id(t.get_text(strip=True),
                                  c.get_text(strip=True) if c else ""),
                    "title": t.get_text(strip=True),
                    "company": c.get_text(strip=True) if c else "Unknown",
                    "location": location, "portal": "Foundit", "url": link,
                })
            except:
                continue
        print(f"  [Foundit]  {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Foundit] Error: {e}")
    return jobs


# ─────────────────────────────────────────
#  EMAIL  (Gmail SMTP only — no Brevo)
# ─────────────────────────────────────────
# AWS Lambda does NOT block outbound SMTP, so Gmail SMTP works directly.
# You need a Gmail App Password (NOT your normal Gmail password).
#
# How to create a Gmail App Password:
#   1. Go to myaccount.google.com → Security
#   2. Enable 2-Step Verification (required)
#   3. Search "App Passwords" → create one named "Job Monitor Bot"
#   4. Copy the 16-character password
#   5. Set it as EMAIL_PASS in Lambda Environment Variables
# ─────────────────────────────────────────

PORTAL_COLORS = {
    "LinkedIn": "#0A66C2",
    "Naukri":   "#FF7555",
    "Indeed":   "#2164f3",
    "Foundit":  "#6C47FF",
}


def build_email_html(job):
    """HTML body for a single job alert."""
    color = PORTAL_COLORS.get(job["portal"], "#6366f1")
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
                <td style="padding:5px 0;color:#333;font-size:14px">{job.get('location', 'India')}</td>
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
                  {datetime.now().strftime('%d %b %Y, %I:%M %p')} IST
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
        </div>
        <div style="background:#f9f9f9;padding:14px 28px;border-top:1px solid #eee">
          <p style="margin:0;color:#aaa;font-size:11px;text-align:center">
            Sent by your Job Monitor Bot · Apply ASAP — early applicants get 3× more callbacks
          </p>
        </div>
      </div>
    </body>
    </html>"""


def send_email_smtp(subject, html):
    """
    Send via Gmail SMTP.
    Tries port 587 (STARTTLS) first, then 465 (SSL) as fallback.
    Both work fine on AWS Lambda — no port blocking.
    """
    user = CONFIG.get("EMAIL_USER", "").strip()
    pwd  = CONFIG.get("EMAIL_PASS", "").strip()
    to   = CONFIG.get("EMAIL_TO",   "").strip()

    if not user or not pwd or not to:
        print("  [Email] ❌ EMAIL_USER / EMAIL_PASS / EMAIL_TO not set in Lambda env vars")
        return False, "missing_config"

    msg = MIMEMultipart("alternative")
    msg["Subject"]    = subject
    msg["From"]       = f"Job Monitor Bot <{user}>"
    msg["To"]         = to
    msg["X-Priority"] = "1"
    msg["Importance"] = "High"
    msg.attach(MIMEText(html, "html"))

    # ── Port 587 STARTTLS (preferred) ──
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True, "587"
    except Exception as e587:
        print(f"  [Email] Port 587 failed: {e587} — trying 465")

    # ── Port 465 SSL (fallback) ──
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True, "465"
    except Exception as e465:
        print(f"  [Email] Port 465 also failed: {e465}")
        return False, str(e465)


def build_digest_email(new_jobs):
    """Single email containing ALL new jobs found in this scan."""
    count = len(new_jobs)
    portal_colors = {
        "LinkedIn": "#0A66C2", "Naukri": "#FF7555",
        "Indeed": "#2164f3",   "Foundit": "#6C47FF",
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
                🏭 {job['company']} &nbsp;·&nbsp; 📍 {job.get('location', 'India')}
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
          <p style="margin:0;color:rgba(255,255,255,0.8);font-size:13px">Job Monitor Bot · AWS Lambda</p>
          <h1 style="margin:6px 0 0;color:#fff;font-size:22px">
            🚨 {count} New Job{'s' if count > 1 else ''} Found!
          </h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:13px">
            {datetime.now().strftime('%d %b %Y, %I:%M %p')} IST
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
#  CORE SCAN LOGIC  (shared by handler)
# ─────────────────────────────────────────

def run_once():
    """
    Runs one full scrape cycle.
    Called by lambda_handler on every EventBridge trigger.
    Returns a summary dict so CloudWatch logs are structured.
    """
    print(f"\n{'='*52}")
    print(f"  🔍 Scan at {datetime.now().strftime('%d %b %Y  %I:%M:%S %p')}")
    print(f"{'='*52}")

    keywords = CONFIG.get("KEYWORDS", ["developer"])
    location = CONFIG.get("LOCATION", "India")
    portals  = CONFIG.get("PORTALS", ["linkedin", "naukri", "indeed", "foundit"])
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
                time.sleep(random.uniform(1, 2))   # shorter than Railway — stay under 15 min timeout

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

    if not new_jobs:
        return {"scanned": len(all_jobs), "new": 0, "email": "skipped"}

    # ── Send ONE digest email with all new jobs ──
    # Instead of one email per job (which wastes quota), we batch everything
    # into a single digest email per Lambda invocation.
    subject = (
        f"🚨 {len(new_jobs)} New Job{'s' if len(new_jobs) > 1 else ''}: "
        f"{new_jobs[0]['title']} @ {new_jobs[0]['company']}"
        + (f" + {len(new_jobs)-1} more" if len(new_jobs) > 1 else "")
    )
    html = build_digest_email(new_jobs)
    ok, detail = send_email_smtp(subject, html)

    if ok:
        print(f"  [Email] ✅ Digest sent via SMTP port {detail} ({len(new_jobs)} jobs)")
        return {"scanned": len(all_jobs), "new": len(new_jobs), "email": f"sent_port_{detail}"}
    else:
        print(f"  [Email] ❌ SMTP failed: {detail}")
        return {"scanned": len(all_jobs), "new": len(new_jobs), "email": f"failed: {detail}"}


# ─────────────────────────────────────────
#  LAMBDA ENTRY POINT
# ─────────────────────────────────────────
# AWS calls this function every time EventBridge fires (every 20 min).
# The `event` dict contains the EventBridge schedule event — we don't need it.
# The `context` object has runtime metadata like remaining time — we don't need it either.
#
# Think of this as replacing your old:
#   while True:
#       run_once()
#       time.sleep(20 * 60)
#
# EventBridge IS the sleep — it wakes Lambda up exactly when needed.
# ─────────────────────────────────────────

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    EventBridge triggers this every 20 minutes.
    """
    print("🚀 Lambda triggered by EventBridge")
    init_db()

    try:
        result = run_once()
        return {
            "statusCode": 200,
            "body": result,
        }
    except Exception as e:
        print(f"  ❌ Unhandled error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
        }


# ─────────────────────────────────────────
#  LOCAL TESTING  (run directly on your machine)
# ─────────────────────────────────────────
# You can still test this file locally before deploying:
#   python job_monitor.py
# It will call lambda_handler once and exit (no loop).
# Set EMAIL_USER / EMAIL_PASS / EMAIL_TO as shell env vars first:
#   export EMAIL_USER=you@gmail.com
#   export EMAIL_PASS=yourapppassword
#   export EMAIL_TO=you@gmail.com

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  ⚡  Job Monitor Bot  —  Local Test Mode  ║")
    print("╚══════════════════════════════════════════╝")
    result = lambda_handler({}, None)
    print(f"\n  Result: {result}")