"""
company_scrapers.py — Enhanced version
Changes:
  1. LinkedIn company-filtered search added for all Indian/global companies
     (fallback when Greenhouse/Lever APIs return 0)
  2. JSearch (RapidAPI) integration — set JSEARCH_API_KEY in Lambda env vars to activate
  3. Adzuna integration — set ADZUNA_APP_ID + ADZUNA_APP_KEY in Lambda env vars to activate
  4. All existing Greenhouse/Lever scrapers kept as primary
"""

import os
import time
from datetime import datetime, timezone, timedelta
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

# ─────────────────────────────────────────────────────────────────────
#  LINKEDIN COMPANY IDs
#  Used for company-filtered LinkedIn search (f_C param)
#  These are the numeric IDs from linkedin.com/company/<slug>
# ─────────────────────────────────────────────────────────────────────
LINKEDIN_COMPANY_IDS = {
    "razorpay":     "2547326",
    "phonepe":      "11172953",
    "paytm":        "1652587",
    "cred":         "19130078",
    "groww":        "9213783",
    "zepto":        "71918462",
    "swiggy":       "3354693",
    "zomato":       "3044872",
    "meesho":       "10634770",
    "flipkart":     "2382148",
    "google":       "1441",
    "microsoft":    "1035",
    "amazon":       "1586",
    "atlassian":    "4303",
    "adobe":        "1441",
    "freshworks":   "3321009",
    "thoughtworks": "1624",
    "zoho":         "1357581",
    "navi":         "17869903",
    "billdesk":     "731467",
    "hsbc":         "2763",
    "nium":         "10876082",
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
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        data = r.json()
    except (requests.exceptions.JSONDecodeError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("data", data.get("postings", []))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("text")]


def safe_greenhouse(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get("jobs", [])
        return []
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────
#  LINKEDIN COMPANY-FILTERED SEARCH
#  Searches LinkedIn jobs filtered to a specific company ID.
#  Works from Lambda since LinkedIn public search is not blocked.
# ─────────────────────────────────────────────────────────────────────

def scrape_linkedin_company(company_name, company_key, keywords, location="India"):
    """
    Search LinkedIn jobs filtered by company ID.
    Uses the f_C (company filter) param on LinkedIn's public job search.
    """
    jobs = []
    company_id = LINKEDIN_COMPANY_IDS.get(company_key.lower())
    if not company_id:
        return jobs

    try:
        url = (
            f"https://www.linkedin.com/jobs/search?"
            f"f_C={company_id}"
            f"&location={requests.utils.quote(location)}"
            f"&f_TPR=r86400"   # last 24 hours
            f"&sortBy=DD"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("div", class_="base-card")[:20]:
            try:
                t = card.find("h3", class_="base-search-card__title")
                c = card.find("h4", class_="base-search-card__subtitle")
                l = card.find("span", class_="job-search-card__location")
                a = card.find("a", class_="base-card__full-link")
                if not t or not a:
                    continue
                title = t.get_text(strip=True)
                if not keyword_matches(title, keywords):
                    continue
                link = a["href"].split("?")[0]
                jobs.append({
                    "id":       make_id("li_company", company_key, link),
                    "title":    title,
                    "company":  company_name,
                    "location": l.get_text(strip=True) if l else location,
                    "portal":   f"{company_name} (LinkedIn)",
                    "url":      link,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"    [LinkedIn/{company_name}] Error: {e}")

    return jobs


# ─────────────────────────────────────────────────────────────────────
#  JSEARCH API (RapidAPI) — activate by setting JSEARCH_API_KEY env var
#  Sign up free at: rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
#  Covers: Naukri, Indeed, LinkedIn, Glassdoor, and more
#
#  COST ESTIMATE (every-20-min Lambda, 1 call/trigger):
#    • Free tier:  200 req/month  →  covers ~2.7 days only
#    • Pro $50/mo: 10,000 req/month → covers full month ✅ ($600/year)
#  RECOMMENDATION: Use Basic ($10/mo) + call once per day as supplement
#    → 30 calls/month → Free tier covers it → $0/year
# ─────────────────────────────────────────────────────────────────────

def _jsearch_should_run():
    """
    Returns True only once per day (IST).
    Uses /tmp/jsearch_last_run.txt to track the last run date.
    Lambda containers persist for hours — if the file has today's date, skip.
    On a cold start the file won't exist, so it runs.
    """
    IST = timezone(timedelta(hours=5, minutes=30))
    today_ist = datetime.now(IST).strftime("%Y-%m-%d")
    flag_file = "/tmp/jsearch_last_run.txt"
    try:
        with open(flag_file, "r") as f:
            if f.read().strip() == today_ist:
                return False  # already ran today
    except FileNotFoundError:
        pass
    try:
        with open(flag_file, "w") as f:
            f.write(today_ist)
    except Exception:
        pass
    return True


def scrape_jsearch(keywords, locations=None, max_results=10):
    """
    JSearch via RapidAPI — aggregates Naukri, Indeed, LinkedIn, Glassdoor.
    Set JSEARCH_API_KEY in Lambda env vars to activate.

    Runs ONCE PER DAY to stay within the free tier.
    Searches all keywords × all locations for comprehensive daily coverage.

    Cost estimate:
      Free tier  200 req/month → you use ~30/month (1/day) → $0/year ✅
      Sign up:   rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    """
    api_key = os.environ.get("JSEARCH_API_KEY", "").strip()
    if not api_key:
        return []

    if not _jsearch_should_run():
        print("  [JSearch]     Skipped (already ran today, saving free tier quota)")
        return []

    if locations is None:
        locations = ["Mumbai", "Pune", "Bangalore"]

    jobs     = []
    seen_ids = set()

    # Fixed keyword: "Software Engineer" — broad enough to cover all variants.
    # 1 call/day × 30 days = 30 req/month → well within free tier (200/month).
    DAILY_KEYWORD = "Software Engineer"
    print(f"  [JSearch]     Daily scan (1 API call, keyword=\"{DAILY_KEYWORD}\", country=India)...")

    try:
        r = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key":  api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={
                "query":       f"{DAILY_KEYWORD} India",
                "page":        "1",
                "num_pages":   "2",        # 2 pages = up to 20 results
                "date_posted": "today",
                "country":     "in",
            },
            timeout=20,
        )
        for job in r.json().get("data", [])[:max_results]:
            title   = job.get("job_title", "")
            company = job.get("employer_name", "Unknown")
            loc_str = job.get("job_city", "") or job.get("job_state", "") or job.get("job_country", "India")
            link    = job.get("job_apply_link") or job.get("job_google_link", "")
            job_id  = job.get("job_id", make_id("jsearch", title, company))
            source  = job.get("job_publisher", "JSearch")

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id":       make_id("jsearch", job_id),
                "title":    title,
                "company":  company,
                "location": loc_str,
                "portal":   source,
                "url":      link,
            })
    except Exception as e:
        print(f"  [JSearch]     Error: {e}")

    print(f"  [JSearch]     {len(jobs)} jobs found (1 API call used today)")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  ADZUNA API — activate by setting ADZUNA_APP_ID + ADZUNA_APP_KEY env vars
#  Register free at: developer.adzuna.com
#  Free tier: 250 calls/day (enough if called once per Lambda trigger)
#
#  COST ESTIMATE (every-20-min Lambda, 1 call/trigger):
#    • Free tier: 250 calls/day, you use 72/day → FREE ✅
#    • Annual cost: $0
#  RECOMMENDATION: Use this — it's completely free for your usage
# ─────────────────────────────────────────────────────────────────────

def scrape_adzuna(keywords, location="Mumbai", max_results=20):
    """
    Adzuna public job API — free tier covers full every-20-min Lambda usage.
    Set ADZUNA_APP_ID and ADZUNA_APP_KEY in Lambda env vars to activate.
    Register at: developer.adzuna.com (free, no credit card)
    """
    app_id  = os.environ.get("ADZUNA_APP_ID",  "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        return []

    jobs = []
    try:
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/in/search/1",
            params={
                "app_id":          app_id,
                "app_key":         app_key,
                "results_per_page": max_results,
                "what":            keywords[0],
                "where":           location,
                "sort_by":         "date",
                "max_days_old":    1,
                "content-type":    "application/json",
            },
            timeout=15,
        )
        for job in r.json().get("results", []):
            title   = job.get("title", "")
            company = job.get("company", {}).get("display_name", "Unknown")
            loc     = job.get("location", {}).get("display_name", location)
            link    = job.get("redirect_url", "https://www.adzuna.in")
            job_id  = str(job.get("id", make_id("adzuna", title, company)))

            if not keyword_matches(title, keywords):
                continue

            jobs.append({
                "id":       make_id("adzuna", job_id),
                "title":    title,
                "company":  company,
                "location": loc,
                "portal":   "Adzuna",
                "url":      link,
            })
        print(f"  [Adzuna]      {len(jobs)} jobs")
    except Exception as e:
        print(f"  [Adzuna]      Error: {e}")

    return jobs


# ─────────────────────────────────────────────────────────────────────
#  INDIAN COMPANY SCRAPERS
#  Strategy: Try Greenhouse/Lever first → fallback to LinkedIn company search
# ─────────────────────────────────────────────────────────────────────

def scrape_with_linkedin_fallback(company_name, company_key, keywords,
                                   greenhouse_slugs=None, lever_slug=None):
    """
    Generic scraper: tries Greenhouse → Lever → LinkedIn company search.
    Returns jobs list.
    """
    jobs = []

    # 1. Try Greenhouse
    if greenhouse_slugs:
        for slug in greenhouse_slugs:
            data = safe_greenhouse(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
            if data:
                for job in data:
                    title = job.get("title", "")
                    if not keyword_matches(title, keywords):
                        continue
                    loc  = (job.get("location") or {}).get("name", "India")
                    link = job.get("absolute_url", "")
                    jobs.append({
                        "id":       make_id(company_key, str(job.get("id", title))),
                        "title":    title,
                        "company":  company_name,
                        "location": loc,
                        "portal":   f"{company_name} Careers",
                        "url":      link,
                    })
                if jobs:
                    return jobs

    # 2. Try Lever
    if lever_slug and not jobs:
        for job in safe_lever(f"https://api.lever.co/v0/postings/{lever_slug}?mode=json"):
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            loc  = (job.get("categories") or {}).get("location", "India")
            link = job.get("hostedUrl", "")
            jobs.append({
                "id":       make_id(company_key, job.get("id", title)),
                "title":    title,
                "company":  company_name,
                "location": loc,
                "portal":   f"{company_name} Careers",
                "url":      link,
            })
        if jobs:
            return jobs

    # 3. Fallback: LinkedIn company-filtered search
    if not jobs:
        li_jobs = scrape_linkedin_company(company_name, company_key, keywords)
        if li_jobs:
            jobs = li_jobs

    return jobs


def scrape_razorpay(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Razorpay", "razorpay", keywords,
        greenhouse_slugs=["razorpay", "razorpayjobs"],
    )
    print(f"  [Razorpay]    {len(jobs)} matching jobs")
    return jobs


def scrape_zepto(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Zepto", "zepto", keywords,
        greenhouse_slugs=["zepto"],
    )
    print(f"  [Zepto]       {len(jobs)} matching jobs")
    return jobs


def scrape_swiggy(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Swiggy", "swiggy", keywords,
        greenhouse_slugs=["swiggy", "swiggyindia", "bundl"],
    )
    print(f"  [Swiggy]      {len(jobs)} matching jobs")
    return jobs


def scrape_cred(keywords):
    jobs = scrape_with_linkedin_fallback(
        "CRED", "cred", keywords,
        greenhouse_slugs=["cred", "dreamplug", "credclub"],
    )
    print(f"  [CRED]        {len(jobs)} matching jobs")
    return jobs


def scrape_meesho(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Meesho", "meesho", keywords,
        greenhouse_slugs=["meesho"],
    )
    print(f"  [Meesho]      {len(jobs)} matching jobs")
    return jobs


def scrape_phonepe(keywords):
    jobs = scrape_with_linkedin_fallback(
        "PhonePe", "phonepe", keywords,
        greenhouse_slugs=["phonepe"],
    )
    print(f"  [PhonePe]     {len(jobs)} matching jobs")
    return jobs


def scrape_groww(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Groww", "groww", keywords,
        greenhouse_slugs=["groww"],
    )
    print(f"  [Groww]       {len(jobs)} matching jobs")
    return jobs


def scrape_paytm(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Paytm", "paytm", keywords,
        greenhouse_slugs=["one97communications", "paytm", "paytmmoney"],
    )
    print(f"  [Paytm]       {len(jobs)} matching jobs")
    return jobs


def scrape_zomato(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Zomato", "zomato", keywords,
        greenhouse_slugs=["zomato", "zomatoindia", "blinkit"],
    )
    print(f"  [Zomato]      {len(jobs)} matching jobs")
    return jobs


def scrape_flipkart(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Flipkart", "flipkart", keywords,
        greenhouse_slugs=["flipkart"],
    )
    print(f"  [Flipkart]    {len(jobs)} matching jobs")
    return jobs


def scrape_freshworks(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Freshworks", "freshworks", keywords,
        greenhouse_slugs=["freshworks"],
        lever_slug="freshworks",
    )
    print(f"  [Freshworks]  {len(jobs)} matching jobs")
    return jobs


def scrape_zoho(keywords):
    jobs = []
    # Try HTML scraping first
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
    except Exception:
        pass

    # Fallback to LinkedIn
    if not jobs:
        jobs = scrape_linkedin_company("Zoho", "zoho", keywords)

    print(f"  [Zoho]        {len(jobs)} matching jobs")
    return jobs


def scrape_thoughtworks(keywords):
    jobs = []
    # Try HTML scraping first
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
    except Exception:
        pass

    # Fallback to LinkedIn
    if not jobs:
        jobs = scrape_linkedin_company("ThoughtWorks", "thoughtworks", keywords)

    print(f"  [ThoughtWorks] {len(jobs)} matching jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  GLOBAL COMPANY SCRAPERS
# ─────────────────────────────────────────────────────────────────────

def scrape_google(keywords):
    jobs = []
    try:
        r = requests.get(
            "https://careers.google.com/jobs/dist/en/all-jobs.json",
            headers={**HEADERS, "Referer": "https://careers.google.com/"},
            timeout=20,
        )
        if "application/json" not in r.headers.get("Content-Type", ""):
            raise Exception("blocked")
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
            jobs.append({"id": make_id("google", title + loc), "title": title,
                "company": "Google", "location": loc,
                "portal": "Google Careers", "url": link})
    except Exception:
        pass

    if not jobs:
        jobs = scrape_linkedin_company("Google", "google", keywords)

    print(f"  [Google]      {len(jobs)} matching jobs")
    return jobs


def scrape_microsoft(keywords):
    jobs = []
    seen_ids = set()
    try:
        for kw in keywords[:3]:
            r = requests.get(
                "https://gcsservices.careers.microsoft.com/search/api/v1/search",
                params={"q": kw, "lc": "India", "l": "en_us",
                        "pg": 1, "pgSz": 10, "o": "Relevance", "flt": "true"},
                headers={**HEADERS, "Accept": "application/json",
                         "Origin": "https://jobs.careers.microsoft.com",
                         "Referer": "https://jobs.careers.microsoft.com/"},
                timeout=20,
            )
            if "application/json" not in r.headers.get("Content-Type", ""):
                continue
            for job in (r.json().get("operationResult", {})
                                .get("result", {}).get("jobs", [])):
                title  = job.get("title", "")
                job_id = str(job.get("jobId", ""))
                if job_id in seen_ids or not keyword_matches(title, keywords):
                    continue
                seen_ids.add(job_id)
                jobs.append({"id": make_id("microsoft", job_id or title),
                    "title": title, "company": "Microsoft",
                    "location": job.get("location", "India"),
                    "portal": "Microsoft Careers",
                    "url": f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"})
    except Exception:
        pass

    if not jobs:
        jobs = scrape_linkedin_company("Microsoft", "microsoft", keywords)

    print(f"  [Microsoft]   {len(jobs)} matching jobs")
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
    except Exception:
        pass

    if not jobs:
        jobs = scrape_linkedin_company("Amazon", "amazon", keywords)

    print(f"  [Amazon]      {len(jobs)} matching jobs")
    return jobs


def scrape_atlassian(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Atlassian", "atlassian", keywords,
        lever_slug="atlassian",
    )
    print(f"  [Atlassian]   {len(jobs)} matching jobs")
    return jobs


def scrape_adobe(keywords):
    jobs = scrape_with_linkedin_fallback(
        "Adobe", "adobe", keywords,
        greenhouse_slugs=["adobe", "adobeindia", "adobesystems"],
    )
    print(f"  [Adobe]       {len(jobs)} matching jobs")
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
            title  = job.get("title", "")
            job_id = job.get("id", "")
            locs   = job.get("locations") or [{}]
            if not keyword_matches(title, keywords):
                continue
            jobs.append({"id": make_id("meta", str(job_id or title)),
                "title": title, "company": "Meta",
                "location": locs[0].get("name", "India"),
                "portal": "Meta Careers",
                "url": f"https://www.metacareers.com/jobs/{job_id}/" if job_id else "https://www.metacareers.com/jobs/"})
    except Exception:
        pass

    print(f"  [Meta]        {len(jobs)} matching jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  NEW COMPANY SCRAPERS (Navi, Billdesk, HSBC, Nium)
# ─────────────────────────────────────────────────────────────────────

def scrape_navi(keywords):
    jobs = scrape_linkedin_company("Navi", "navi", keywords)
    print(f"  [Navi]        {len(jobs)} matching jobs")
    return jobs


def scrape_billdesk(keywords):
    jobs = scrape_linkedin_company("BillDesk", "billdesk", keywords)
    print(f"  [BillDesk]    {len(jobs)} matching jobs")
    return jobs


def scrape_hsbc(keywords):
    jobs = []
    # HSBC has a public careers API
    try:
        r = requests.get(
            "https://mycareer.hsbc.com/en_GB/external/SearchJobs",
            params={"SearchJobsQuery": keywords[0], "SearchLocation": "India"},
            headers=HEADERS, timeout=15,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                t = a.find(["h3", "h4", "span"])
                if not t:
                    continue
                title = t.get_text(strip=True)
                if not (5 < len(title) < 120) or not keyword_matches(title, keywords):
                    continue
                href = a["href"]
                link = href if href.startswith("http") else f"https://mycareer.hsbc.com{href}"
                jobs.append({"id": make_id("hsbc", title),
                    "title": title, "company": "HSBC",
                    "location": "India", "portal": "HSBC Careers", "url": link})
    except Exception:
        pass

    # Fallback to LinkedIn
    if not jobs:
        jobs = scrape_linkedin_company("HSBC", "hsbc", keywords)

    print(f"  [HSBC]        {len(jobs)} matching jobs")
    return jobs


def scrape_nium(keywords):
    jobs = []
    # Nium uses Greenhouse
    for slug in ["nium", "niumhq"]:
        data = safe_greenhouse(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        if data:
            for job in data:
                title = job.get("title", "")
                if not keyword_matches(title, keywords):
                    continue
                loc  = (job.get("location") or {}).get("name", "India")
                link = job.get("absolute_url", "https://www.nium.com/careers")
                jobs.append({"id": make_id("nium", str(job.get("id", title))),
                    "title": title, "company": "Nium",
                    "location": loc, "portal": "Nium Careers", "url": link})
            if jobs:
                break

    # Fallback to LinkedIn
    if not jobs:
        jobs = scrape_linkedin_company("Nium", "nium", keywords)

    print(f"  [Nium]        {len(jobs)} matching jobs")
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
    "navi":         scrape_navi,
    "billdesk":     scrape_billdesk,
    "hsbc":         scrape_hsbc,
    "nium":         scrape_nium,
}


def scrape_companies(keywords):
    from config import CONFIG
    targets = CONFIG.get("COMPANY_TARGETS", [])
    if not targets:
        return []

    # ── JSearch (once per day) + Adzuna (every trigger) ──────────────
    all_jobs = []
    locations = CONFIG.get("LOCATION", ["Mumbai", "Pune", "Bangalore"])
    if isinstance(locations, str):
        locations = [locations]

    jsearch_jobs = scrape_jsearch(keywords, locations=locations)
    adzuna_jobs  = scrape_adzuna(keywords)
    if jsearch_jobs:
        all_jobs.extend(jsearch_jobs)
    if adzuna_jobs:
        all_jobs.extend(adzuna_jobs)

    print(f"\n🏢 Company Portals ({len(targets)} companies):")
    for company in targets:
        key = company.strip().lower()
        if key in COMPANY_SCRAPERS:
            try:
                all_jobs.extend(COMPANY_SCRAPERS[key](keywords))
                time.sleep(0.5)   # small delay between companies
            except Exception as e:
                print(f"  [{company}] Unexpected error: {e}")
        else:
            print(f"  [{company}] ⚠️  No scraper found")

    return all_jobs