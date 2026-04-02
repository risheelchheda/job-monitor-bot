"""
job_monitor.py  —  AWS Lambda version
Changes in this version:
  1. Individual email per job (not a digest)
  2. Naukri  — switched to their internal JSON API (no JS rendering needed)
  3. Indeed  — switched to their internal JSON API
  4. Foundit — switched to their search JSON API
  5. LinkedIn — kept as-is (still works via HTML)
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import hashlib
import random
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import CONFIG
from company_scrapers import scrape_companies

# ─────────────────────────────────────────
#  DATABASE  (/tmp — Lambda writable space)
# ─────────────────────────────────────────

DB_PATH = "/tmp/jobs.db"


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
#  SCRAPERS
# ─────────────────────────────────────────

def make_id(*parts):
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


HEADERS_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/html, */*",
}


# ── LinkedIn (HTML scraping still works) ──────────────────────────────

def scrape_linkedin(keyword, location="India"):
    jobs = []
    try:
        url = (
            f"https://www.linkedin.com/jobs/search?"
            f"keywords={requests.utils.quote(keyword)}"
            f"&location={requests.utils.quote(location)}"
            f"&f_TPR=r3600&sortBy=DD"
        )
        r = requests.get(url, headers=HEADERS_BROWSER, timeout=15)
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
                    "id":       make_id(link),
                    "title":    t.get_text(strip=True),
                    "company":  c.get_text(strip=True) if c else "Unknown",
                    "location": l.get_text(strip=True) if l else "",
                    "portal":   "LinkedIn",
                    "url":      link,
                })
            except:
                continue
        print(f"  [LinkedIn] {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")
    return jobs


# ── Naukri (JSON API — replaces broken HTML scraping) ─────────────────
# Naukri's public job search API returns clean JSON — no JS rendering needed.

def scrape_naukri(keyword, location="india"):
    jobs = []
    try:
        headers = {
            **HEADERS_BROWSER,
            "Accept":          "application/json",
            "Referer":         "https://www.naukri.com/",
            "appid":           "109",
            "systemid":        "109",
        }
        params = {
            "noOfResults": 20,
            "urlType":     "search_by_keyword",
            "searchType":  "adv",
            "keyword":     keyword,
            "location":    location,
            "pageNo":      1,
            "k":           keyword,
            "l":           location,
            "seoKey":      f"{keyword.lower().replace(' ', '-')}-jobs",
            "src":         "jobsearchDesk",
            "latLong":     "",
        }
        r = requests.get(
            "https://www.naukri.com/jobapi/v3/search",
            params=params,
            headers=headers,
            timeout=15,
        )
        data = r.json()

        for job in data.get("jobDetails", []):
            title   = job.get("title", "")
            company = job.get("companyName", "Unknown")
            loc     = ", ".join(job.get("placeholders", [{}])[0].get("label", "India").split(",")[:2]) \
                      if job.get("placeholders") else "India"
            link    = job.get("jdURL", "") or f"https://www.naukri.com/job-listings-{make_id(title, company)}"
            job_id  = str(job.get("jobId", make_id(title, company)))

            jobs.append({
                "id":       make_id("naukri", job_id),
                "title":    title,
                "company":  company,
                "location": loc,
                "portal":   "Naukri",
                "url":      link if link.startswith("http") else f"https://www.naukri.com{link}",
            })

        print(f"  [Naukri]   {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Naukri]   Error: {e}")
    return jobs


# ── Indeed (JSON API — replaces broken HTML scraping) ─────────────────
# Indeed's mosaic API returns structured JSON directly.

def scrape_indeed(keyword, location="India"):
    jobs = []
    try:
        headers = {
            **HEADERS_BROWSER,
            "Accept":   "application/json, text/javascript, */*; q=0.01",
            "Referer":  "https://in.indeed.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        params = {
            "q":        keyword,
            "l":        location,
            "fromage":  "3",       # posted in last 3 days
            "sort":     "date",
            "limit":    "20",
            "radius":   "50",
            "filter":   "0",
            "start":    "0",
            "format":   "json",
        }
        r = requests.get(
            "https://in.indeed.com/jobs",
            params=params,
            headers=headers,
            timeout=15,
        )

        # Indeed sometimes returns HTML even with format=json — parse both
        content_type = r.headers.get("Content-Type", "")
        if "json" in content_type:
            results = r.json().get("results", [])
            for job in results[:20]:
                title   = job.get("jobtitle", "")
                company = job.get("company", "Unknown")
                loc     = job.get("formattedLocation", location)
                job_key = job.get("jobkey", "")
                link    = f"https://in.indeed.com/viewjob?jk={job_key}" if job_key else "https://in.indeed.com"
                jobs.append({
                    "id":       make_id("indeed", job_key or title + company),
                    "title":    title,
                    "company":  company,
                    "location": loc,
                    "portal":   "Indeed",
                    "url":      link,
                })
        else:
            # Fallback: parse HTML but with updated selectors
            soup = BeautifulSoup(r.text, "html.parser")

            # Try new-style cards first (2024 layout)
            cards = soup.find_all("div", attrs={"data-testid": "slider_item"})
            if not cards:
                cards = soup.find_all("div", class_="job_seen_beacon")
            if not cards:
                # Try extracting from embedded JSON in page
                script = soup.find("script", id="mosaic-provider-jobcards")
                if script:
                    try:
                        raw = script.string
                        start = raw.index("jobKeysWithInfo") + len("jobKeysWithInfo") + 2
                        # parse embedded job data
                        pass
                    except:
                        pass

            for card in cards[:20]:
                try:
                    t = (card.find("h2", attrs={"data-testid": "jobTitle"}) or
                         card.find("h2", class_="jobTitle") or
                         card.find("span", attrs={"title": True}))
                    c = (card.find("span", attrs={"data-testid": "company-name"}) or
                         card.find("span", class_="companyName"))
                    l = (card.find("div",  attrs={"data-testid": "text-location"}) or
                         card.find("div",  class_="companyLocation"))
                    a = card.find("a", href=True)
                    if not t:
                        continue
                    href = a.get("href", "") if a else ""
                    link = f"https://in.indeed.com{href}" if href.startswith("/") else href
                    title_text = t.get_text(strip=True).replace("new", "").strip()
                    jobs.append({
                        "id":       make_id("indeed", link or title_text),
                        "title":    title_text,
                        "company":  c.get_text(strip=True) if c else "Unknown",
                        "location": l.get_text(strip=True) if l else location,
                        "portal":   "Indeed",
                        "url":      link,
                    })
                except:
                    continue

        print(f"  [Indeed]   {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Indeed]   Error: {e}")
    return jobs


# ── Foundit (JSON API — replaces broken HTML scraping) ────────────────
# Foundit exposes a public search API that returns clean JSON.

def scrape_foundit(keyword, location="India"):
    jobs = []
    try:
        headers = {
            **HEADERS_BROWSER,
            "Accept":          "application/json",
            "Referer":         "https://www.foundit.in/",
            "Origin":          "https://www.foundit.in",
        }
        payload = {
            "query":         keyword,
            "locationName":  location,
            "expectedSalary": 0,
            "freshnessInDays": 7,
            "start":         0,
            "rows":          20,
            "sort":          1,        # 1 = most recent
        }
        r = requests.post(
            "https://www.foundit.in/middleware/jobsearch/v2/search",
            json=payload,
            headers=headers,
            timeout=15,
        )
        data = r.json()

        for job in data.get("jobSearchResponse", {}).get("data", []):
            title   = job.get("designation", "")
            company = job.get("company", {}).get("name", "Unknown") \
                      if isinstance(job.get("company"), dict) else str(job.get("company", "Unknown"))
            loc     = job.get("location", location)
            if isinstance(loc, list):
                loc = ", ".join(loc[:2])
            job_id  = str(job.get("id", ""))
            link    = f"https://www.foundit.in/job/{job_id}" if job_id else "https://www.foundit.in"

            jobs.append({
                "id":       make_id("foundit", job_id or title + company),
                "title":    title,
                "company":  company,
                "location": loc,
                "portal":   "Foundit",
                "url":      link,
            })

        print(f"  [Foundit]  {len(jobs)} jobs for '{keyword}'")
    except Exception as e:
        print(f"  [Foundit]  Error: {e}")
    return jobs


# ─────────────────────────────────────────
#  EMAIL — one individual email per job
# ─────────────────────────────────────────

PORTAL_COLORS = {
    "LinkedIn":  "#0A66C2",
    "Naukri":    "#FF7555",
    "Indeed":    "#2164f3",
    "Foundit":   "#6C47FF",
}


def build_email_html(job):
    """Builds a rich HTML email for a single job posting."""
    color = PORTAL_COLORS.get(job["portal"], "#6366f1")
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
  <div style="max-width:580px;margin:30px auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,0.08)">

    <!-- Header -->
    <div style="background:{color};padding:24px 28px">
      <p style="margin:0;color:rgba(255,255,255,0.8);font-size:13px">Job Monitor Bot</p>
      <h1 style="margin:4px 0 0;color:#fff;font-size:22px">🚨 New Job Alert!</h1>
    </div>

    <!-- Job details -->
    <div style="padding:24px 28px">
      <div style="background:#fafafa;border:1px solid #eee;border-radius:10px;padding:20px">
        <h2 style="margin:0 0 16px;color:#1a1a2e;font-size:20px">{job['title']}</h2>
        <table style="border-collapse:collapse;width:100%">
          <tr>
            <td style="padding:6px 0;color:#888;font-size:13px;width:90px">🏭 Company</td>
            <td style="padding:6px 0;color:#333;font-size:14px;font-weight:600">{job['company']}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#888;font-size:13px">📍 Location</td>
            <td style="padding:6px 0;color:#333;font-size:14px">{job.get('location', 'India')}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#888;font-size:13px">🌐 Source</td>
            <td style="padding:6px 0">
              <span style="background:{color}20;color:{color};padding:2px 10px;
                           border-radius:20px;font-size:12px;font-weight:700">{job['portal']}</span>
            </td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#888;font-size:13px">⏰ Found</td>
            <td style="padding:6px 0;color:#333;font-size:14px">
              {datetime.now().strftime('%d %b %Y, %I:%M %p')} IST
            </td>
          </tr>
        </table>
      </div>

      <!-- CTA button -->
      <a href="{job['url']}"
         style="display:block;text-align:center;margin:20px 0 0;padding:14px;
                background:{color};color:#fff;text-decoration:none;border-radius:8px;
                font-weight:700;font-size:16px;letter-spacing:0.3px">
        ⚡ Apply Now — Be Among the First!
      </a>
    </div>

    <!-- Footer -->
    <div style="background:#f9f9f9;padding:14px 28px;border-top:1px solid #eee">
      <p style="margin:0;color:#aaa;font-size:11px;text-align:center">
        Job Monitor Bot · Apply ASAP — early applicants get 3× more callbacks
      </p>
    </div>
  </div>
</body>
</html>"""


def send_email_smtp(subject, html):
    """
    Send via Gmail SMTP.
    Tries port 587 (STARTTLS) first, then 465 (SSL) as fallback.
    """
    user = CONFIG.get("EMAIL_USER", "").strip()
    pwd  = CONFIG.get("EMAIL_PASS", "").strip()
    to   = CONFIG.get("EMAIL_TO",   "").strip()

    if not user or not pwd or not to:
        print("  [Email] ❌ EMAIL_USER / EMAIL_PASS / EMAIL_TO not set")
        return False, "missing_config"

    msg = MIMEMultipart("alternative")
    msg["Subject"]    = subject
    msg["From"]       = f"Job Monitor Bot <{user}>"
    msg["To"]         = to
    msg["X-Priority"] = "1"
    msg["Importance"] = "High"
    msg.attach(MIMEText(html, "html"))

    # Port 587 — STARTTLS
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

    # Port 465 — SSL fallback
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True, "465"
    except Exception as e465:
        return False, str(e465)


# ─────────────────────────────────────────
#  CORE SCAN LOGIC
# ─────────────────────────────────────────

def run_once():
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
                time.sleep(random.uniform(1, 2))

    # Company career portals
    all_jobs += scrape_companies(keywords)

    # Deduplicate within this scan (same job from multiple keyword searches)
    seen_this_scan = set()
    unique_jobs = []
    for job in all_jobs:
        if job["id"] not in seen_this_scan:
            seen_this_scan.add(job["id"])
            unique_jobs.append(job)

    # Find genuinely new jobs (not seen in any previous scan)
    new_jobs = []
    for job in unique_jobs:
        if is_new_job(job["id"]):
            print(f"  🆕 NEW: {job['title']} @ {job['company']} [{job['portal']}]")
            save_job(job)
            new_jobs.append(job)

    print(f"\n  ✅ {len(new_jobs)} new job(s) | {len(unique_jobs)} unique | {len(all_jobs)} total scanned")

    if not new_jobs:
        return {"scanned": len(all_jobs), "new": 0, "emails_sent": 0}

    # ── Send ONE individual email per new job ──────────────────────────
    # Each job gets its own email so your inbox shows individual alerts.
    # You can see at a glance: "Backend Engineer @ Razorpay" without
    # opening a digest. Easier to act on / archive per job.
    emails_sent = 0
    for job in new_jobs:
        subject = f"⚡ {job['title']} @ {job['company']} [{job['portal']}]"
        html    = build_email_html(job)
        label   = f"{job['title']} @ {job['company']}"

        ok, detail = send_email_smtp(subject, html)
        if ok:
            print(f"  [Email] ✅ Sent (port {detail}) → {label}")
            emails_sent += 1
        else:
            print(f"  [Email] ❌ Failed ({detail}) → {label}")

        time.sleep(1)   # small gap between emails to avoid Gmail rate limiting

    return {"scanned": len(all_jobs), "new": len(new_jobs), "emails_sent": emails_sent}


# ─────────────────────────────────────────
#  LAMBDA ENTRY POINT
# ─────────────────────────────────────────

def lambda_handler(event, context):
    """AWS Lambda entry point — triggered by EventBridge every N minutes."""
    print("🚀 Lambda triggered by EventBridge")
    init_db()

    try:
        result = run_once()
        return {"statusCode": 200, "body": result}
    except Exception as e:
        print(f"  ❌ Unhandled error: {e}")
        return {"statusCode": 500, "body": {"error": str(e)}}


# ─────────────────────────────────────────
#  LOCAL TESTING
# ─────────────────────────────────────────
# export EMAIL_USER=you@gmail.com
# export EMAIL_PASS=yourapppassword
# export EMAIL_TO=you@gmail.com
# python job_monitor.py

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  ⚡  Job Monitor Bot  —  Local Test Mode  ║")
    print("╚══════════════════════════════════════════╝")
    result = lambda_handler({}, None)
    print(f"\n  Result: {result}")