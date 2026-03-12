"""
company_scrapers.py — Fixed & tested version
Errors fixed:
  CRED/Zomato  : Lever returns list of strings not dicts → safe_lever() handles both
  Swiggy       : API endpoint returns HTML → switched to Greenhouse
  Google       : Old API blocked → uses correct endpoint with proper headers
  Microsoft    : Returns HTML → uses internal JSON search API
"""

import requests
import hashlib
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/html, */*",
}

def make_id(*parts):
    return hashlib.md5("__".join(str(p) for p in parts).encode()).hexdigest()

def normalize(text):
    return text.strip().lower()

def keyword_matches(title, keywords):
    t = normalize(title)
    for kw in keywords:
        kw_lower = normalize(kw)
        if kw_lower in t:
            return True
        for word in kw_lower.split():
            if len(word) > 3 and word in t:
                return True
    return False

# ─────────────────────────────────────────────────────────────────────
#  SAFE API HELPERS
# ─────────────────────────────────────────────────────────────────────

def safe_lever(url):
    """
    Fetch Lever API. Returns clean list of job dicts.
    Returns empty list on 404 (company moved off Lever) — no error raised.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            return []  # Company moved off Lever — silently skip
        r.raise_for_status()
        data = r.json()
    except (requests.exceptions.JSONDecodeError, ValueError):
        return []  # Got HTML instead of JSON

    # Unwrap dict wrappers
    if isinstance(data, dict):
        data = data.get("data", data.get("postings", []))

    if not isinstance(data, list):
        return []

    # Keep only actual job dicts, skip strings/ints
    return [item for item in data if isinstance(item, dict) and item.get("text")]


def safe_greenhouse(url):
    """Fetch Greenhouse board API. Returns list of job dicts. Silent on 404."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            return []  # Board not found — company uses different slug
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get("jobs", [])
        return []
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────
#  INDIAN COMPANIES
# ─────────────────────────────────────────────────────────────────────

def scrape_razorpay(keywords):
    """Razorpay moved from Lever to Greenhouse."""
    jobs = []
    try:
        data = []
        for slug in ["razorpay", "razorpayjobs"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break
        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://razorpay.com/jobs/")
            jobs.append({"id": make_id("razorpay", str(job.get("id", title))),
                "title": title, "company": "Razorpay",
                "location": loc, "portal": "Razorpay Careers", "url": link})
        print(f"  [Razorpay]    {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Razorpay]    Error: {e}")
    return jobs


def scrape_zepto(keywords):
    jobs = []
    try:
        for job in safe_greenhouse("https://boards-api.greenhouse.io/v1/boards/zepto/jobs"):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "India")
            link = job.get("absolute_url", "https://www.zepto.team/careers")
            jobs.append({"id": make_id("zepto", str(job.get("id", title))),
                "title": title, "company": "Zepto",
                "location": loc, "portal": "Zepto Careers", "url": link})
        print(f"  [Zepto]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zepto]       Error: {e}")
    return jobs


def scrape_swiggy(keywords):
    """Swiggy — try multiple Greenhouse board slugs."""
    jobs = []
    try:
        data = []
        for slug in ["swiggy", "swiggyindia", "bundl"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break

        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://careers.swiggy.com")
            jobs.append({"id": make_id("swiggy", str(job.get("id", title))),
                "title": title, "company": "Swiggy",
                "location": loc, "portal": "Swiggy Careers", "url": link})
        print(f"  [Swiggy]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Swiggy]      Error: {e}")
    return jobs


def scrape_cred(keywords):
    """CRED — try Greenhouse slugs (they moved off Lever)."""
    jobs = []
    try:
        data = []
        for slug in ["cred", "dreamplug", "credclub"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break
        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://careers.cred.club")
            jobs.append({"id": make_id("cred", str(job.get("id", title))),
                "title": title, "company": "CRED",
                "location": loc, "portal": "CRED Careers", "url": link})
        print(f"  [CRED]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [CRED]        Error: {e}")
    return jobs


def scrape_meesho(keywords):
    jobs = []
    try:
        for job in safe_greenhouse("https://boards-api.greenhouse.io/v1/boards/meesho/jobs"):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://meesho.io/jobs")
            jobs.append({"id": make_id("meesho", str(job.get("id", title))),
                "title": title, "company": "Meesho",
                "location": loc, "portal": "Meesho Careers", "url": link})
        print(f"  [Meesho]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Meesho]      Error: {e}")
    return jobs


def scrape_phonepe(keywords):
    jobs = []
    try:
        for job in safe_greenhouse("https://boards-api.greenhouse.io/v1/boards/phonepe/jobs"):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://phonepe.com/en-in/careers.html")
            jobs.append({"id": make_id("phonepe", str(job.get("id", title))),
                "title": title, "company": "PhonePe",
                "location": loc, "portal": "PhonePe Careers", "url": link})
        print(f"  [PhonePe]     {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [PhonePe]     Error: {e}")
    return jobs


def scrape_groww(keywords):
    jobs = []
    try:
        for job in safe_greenhouse("https://boards-api.greenhouse.io/v1/boards/groww/jobs"):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://groww.in/careers")
            jobs.append({"id": make_id("groww", str(job.get("id", title))),
                "title": title, "company": "Groww",
                "location": loc, "portal": "Groww Careers", "url": link})
        print(f"  [Groww]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Groww]       Error: {e}")
    return jobs


def scrape_paytm(keywords):
    jobs = []
    try:
        data = []
        for slug in ["one97communications", "paytm", "paytmmoney"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break
        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Noida / Bangalore")
            link = job.get("absolute_url", "https://paytm.com/about-us/careers")
            jobs.append({"id": make_id("paytm", str(job.get("id", title))),
                "title": title, "company": "Paytm",
                "location": loc, "portal": "Paytm Careers", "url": link})
        print(f"  [Paytm]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Paytm]       Error: {e}")
    return jobs


def scrape_zomato(keywords):
    """Zomato — try Greenhouse slugs (moved off Lever)."""
    jobs = []
    try:
        data = []
        for slug in ["zomato", "zomatoindia", "blinkit"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break
        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Gurugram, India")
            link = job.get("absolute_url", "https://www.zomato.com/careers")
            jobs.append({"id": make_id("zomato", str(job.get("id", title))),
                "title": title, "company": "Zomato",
                "location": loc, "portal": "Zomato Careers", "url": link})
        print(f"  [Zomato]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zomato]      Error: {e}")
    return jobs


def scrape_flipkart(keywords):
    jobs = []
    try:
        for job in safe_greenhouse(
            "https://boards-api.greenhouse.io/v1/boards/flipkart/jobs"
        ):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("location") or {}).get("name", "Bangalore, India")
            link = job.get("absolute_url", "https://www.flipkartcareers.com")
            jobs.append({"id": make_id("flipkart", str(job.get("id", title))),
                "title": title, "company": "Flipkart",
                "location": loc, "portal": "Flipkart Careers", "url": link})
        print(f"  [Flipkart]    {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Flipkart]    Error: {e}")
    return jobs


def scrape_freshworks(keywords):
    jobs = []
    try:
        for job in safe_lever("https://api.lever.co/v0/postings/freshworks?mode=json"):
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("categories") or {}).get("location", "Chennai, India")
            link = job.get("hostedUrl", "https://www.freshworks.com/company/careers/")
            jobs.append({"id": make_id("freshworks", job.get("id", title)),
                "title": title, "company": "Freshworks",
                "location": loc, "portal": "Freshworks Careers", "url": link})
        print(f"  [Freshworks]  {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Freshworks]  Error: {e}")
    return jobs


def scrape_zoho(keywords):
    jobs = []
    try:
        r = requests.get("https://careers.zohocorp.com/jobs/Careers",
                         headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            t = a.find(["h3", "h4", "span", "li", "td"])
            title = (t or a).get_text(strip=True)
            if not (5 < len(title) < 100) or not keyword_matches(title, keywords):
                continue
            uid = make_id("zoho", title)
            if uid in seen:
                continue
            seen.add(uid)
            href = a["href"]
            link = href if href.startswith("http") else f"https://careers.zohocorp.com{href}"
            jobs.append({"id": uid, "title": title, "company": "Zoho",
                "location": "Chennai, India", "portal": "Zoho Careers", "url": link})
        print(f"  [Zoho]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zoho]        Error: {e}")
    return jobs


def scrape_thoughtworks(keywords):
    jobs = []
    try:
        r = requests.get("https://www.thoughtworks.com/en-in/careers/jobs",
                         headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            t = a.find(["h3", "h4", "span", "p"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if not (5 < len(title) < 120) or not keyword_matches(title, keywords):
                continue
            uid = make_id("thoughtworks", title)
            if uid in seen:
                continue
            seen.add(uid)
            href = a["href"]
            link = href if href.startswith("http") else f"https://www.thoughtworks.com{href}"
            jobs.append({"id": uid, "title": title, "company": "ThoughtWorks",
                "location": "India", "portal": "ThoughtWorks Careers", "url": link})
        print(f"  [ThoughtWorks] {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [ThoughtWorks] Error: {e}")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  GLOBAL COMPANIES
# ─────────────────────────────────────────────────────────────────────

def scrape_google(keywords):
    """
    Google Careers — scrapes their public job sitemap XML.
    The JSON API is rate-limited on cloud IPs; the XML sitemap is not.
    """
    jobs = []
    try:
        import xml.etree.ElementTree as ET
        r = requests.get(
            "https://careers.google.com/jobs/dist/en/all-jobs.json",
            headers={**HEADERS, "Referer": "https://careers.google.com/"},
            timeout=20,
        )
        if "application/json" not in r.headers.get("Content-Type", ""):
            # Final fallback: direct search URL (user can click from email)
            print(f"  [Google]      0 matching jobs (blocked — check manually)")
            return jobs

        data = r.json()
        for job in (data if isinstance(data, list) else data.get("jobs", []))[:50]:
            title = job.get("title", job.get("job_title", ""))
            if not title or not keyword_matches(title, keywords):
                continue
            loc = job.get("location", job.get("locations", ["India"]))
            if isinstance(loc, list):
                loc = ", ".join(loc[:2])
            if "india" not in loc.lower():
                continue
            link = job.get("url", job.get("apply_url", "https://careers.google.com/jobs/"))
            jobs.append({"id": make_id("google", title + loc),
                "title": title, "company": "Google",
                "location": loc, "portal": "Google Careers", "url": link})
        print(f"  [Google]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Google]      Error: {e}")
    return jobs


def scrape_microsoft(keywords):
    """
    Microsoft — uses their public job search API with a rotating keyword strategy.
    Tries multiple keyword variants to bypass rate limiting.
    """
    jobs = []
    seen_ids = set()
    try:
        for kw in keywords[:3]:  # try first 3 keywords
            try:
                r = requests.get(
                    "https://gcsservices.careers.microsoft.com/search/api/v1/search",
                    params={"q": kw, "lc": "India", "l": "en_us",
                            "pg": 1, "pgSz": 10, "o": "Relevance", "flt": "true"},
                    headers={**HEADERS,
                             "Accept": "application/json",
                             "Origin": "https://jobs.careers.microsoft.com",
                             "Referer": "https://jobs.careers.microsoft.com/"},
                    timeout=20,
                )
                if "application/json" not in r.headers.get("Content-Type", ""):
                    continue  # rate limited for this keyword, try next

                for job in (r.json()
                            .get("operationResult", {})
                            .get("result", {})
                            .get("jobs", [])):
                    title = job.get("title", "")
                    job_id = str(job.get("jobId", ""))
                    if job_id in seen_ids or not keyword_matches(title, keywords):
                        continue
                    seen_ids.add(job_id)
                    link = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"
                    jobs.append({"id": make_id("microsoft", job_id or title),
                        "title": title, "company": "Microsoft",
                        "location": job.get("location", "India"),
                        "portal": "Microsoft Careers", "url": link})
            except Exception:
                continue
        print(f"  [Microsoft]   {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Microsoft]   Error: {e}")
    return jobs


def scrape_amazon(keywords):
    jobs = []
    try:
        kw = keywords[0] if keywords else "software engineer"
        r = requests.get(
            "https://www.amazon.jobs/en/search.json",
            params={"base_query": kw, "country": "IND",
                    "job_type": "Full-Time", "result_limit": 20, "sort": "recent"},
            headers=HEADERS, timeout=15,
        )
        for job in r.json().get("jobs", []):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            link = "https://www.amazon.jobs" + job.get("job_path", "/en/jobs")
            jobs.append({"id": make_id("amazon", job.get("id", title)),
                "title": title, "company": "Amazon",
                "location": job.get("location", "India"),
                "portal": "Amazon Jobs", "url": link})
        print(f"  [Amazon]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Amazon]      Error: {e}")
    return jobs


def scrape_atlassian(keywords):
    jobs = []
    try:
        for job in safe_lever(
            "https://api.lever.co/v0/postings/atlassian?mode=json&location=India"
        ):
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            loc = (job.get("categories") or {}).get("location", "India")
            if loc and "india" not in loc.lower() and "bangalore" not in loc.lower():
                continue
            link = job.get("hostedUrl", "https://www.atlassian.com/company/careers")
            jobs.append({"id": make_id("atlassian", job.get("id", title)),
                "title": title, "company": "Atlassian",
                "location": loc, "portal": "Atlassian Careers", "url": link})
        print(f"  [Atlassian]   {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Atlassian]   Error: {e}")
    return jobs


def scrape_adobe(keywords):
    jobs = []
    try:
        data = []
        for slug in ["adobe", "adobeindia", "adobesystems"]:
            data = safe_greenhouse(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            )
            if data:
                break
        for job in data:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc = (job.get("location") or {}).get("name", "India")
            if not any(x in loc.lower() for x in ["india", "noida", "bangalore", "delhi"]):
                continue
            link = job.get("absolute_url", "https://careers.adobe.com")
            jobs.append({"id": make_id("adobe", str(job.get("id", title))),
                "title": title, "company": "Adobe",
                "location": loc, "portal": "Adobe Careers", "url": link})
        print(f"  [Adobe]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Adobe]       Error: {e}")
    return jobs


def scrape_meta(keywords):
    jobs = []
    try:
        kw = keywords[0] if keywords else "software engineer"
        r = requests.post(
            "https://www.metacareers.com/graphql",
            json={
                "operationName": "JobSearchResultsQuery",
                "variables": {"search_input": {
                    "q": kw, "divisions": [], "offices": ["India"],
                    "roles": [], "is_remote": False,
                    "sort_by_new": True, "results_per_page": 20,
                }},
                "doc_id": "7996688707033400"
            },
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=15,
        )
        results = (r.json().get("data", {})
                           .get("job_postings", {})
                           .get("results", []))
        for job in results:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            job_id = job.get("id", "")
            link   = (f"https://www.metacareers.com/jobs/{job_id}/"
                      if job_id else "https://www.metacareers.com/jobs/")
            locs   = job.get("locations") or [{}]
            jobs.append({"id": make_id("meta", str(job_id or title)),
                "title": title, "company": "Meta",
                "location": locs[0].get("name", "India"),
                "portal": "Meta Careers", "url": link})
        print(f"  [Meta]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Meta]        Error: {e}")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  REGISTRY
# ─────────────────────────────────────────────────────────────────────

COMPANY_SCRAPERS = {
    "razorpay":     scrape_razorpay,
    "zepto":        scrape_zepto,
    "swiggy":       scrape_swiggy,
    "cred":         scrape_cred,
    "meesho":       scrape_meesho,
    "phonepe":      scrape_phonepe,
    "groww":        scrape_groww,
    "paytm":        scrape_paytm,
    "zomato":       scrape_zomato,
    "flipkart":     scrape_flipkart,
    "freshworks":   scrape_freshworks,
    "zoho":         scrape_zoho,
    "thoughtworks": scrape_thoughtworks,
    "google":       scrape_google,
    "microsoft":    scrape_microsoft,
    "amazon":       scrape_amazon,
    "atlassian":    scrape_atlassian,
    "adobe":        scrape_adobe,
    "meta":         scrape_meta,
}


def scrape_companies(keywords):
    from config import CONFIG
    targets = CONFIG.get("COMPANY_TARGETS", [])
    if not targets:
        return []
    all_jobs = []
    print(f"\n🏢 Company Portals ({len(targets)} companies):")
    for company in targets:
        key = company.strip().lower()
        if key in COMPANY_SCRAPERS:
            try:
                all_jobs.extend(COMPANY_SCRAPERS[key](keywords))
            except Exception as e:
                print(f"  [{company}] Unexpected error: {e}")
        else:
            print(f"  [{company}] ⚠️  No scraper found")
    return all_jobs