"""
company_scrapers.py
Scrapes career pages of individual companies directly.
Each scraper returns a list of job dicts matching the same format
as the portal scrapers in job_monitor.py

Add your target companies in config.py → COMPANY_TARGETS list.
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
    "Accept": "application/json, text/html,*/*",
}

def make_id(*parts):
    return hashlib.md5("__".join(parts).encode()).hexdigest()

def normalize(title):
    return title.strip().lower()

def keyword_matches(title, keywords):
    """Check if any keyword matches the job title (case-insensitive)."""
    t = normalize(title)
    return any(normalize(kw) in t or
               any(w in t for w in normalize(kw).split())
               for kw in keywords)

# ─────────────────────────────────────────────────────────────────────
#  INDIAN PRODUCT / STARTUP COMPANIES
# ─────────────────────────────────────────────────────────────────────

def scrape_razorpay(keywords):
    jobs = []
    try:
        url = "https://razorpay.com/jobs/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("a", href=True):
            title_tag = card.find("h3") or card.find("h4") or card.find("p", class_=lambda c: c and "title" in (c or ""))
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if not title or not keyword_matches(title, keywords):
                continue
            href = card["href"]
            link = href if href.startswith("http") else f"https://razorpay.com{href}"
            jobs.append({"id": make_id("razorpay", title), "title": title,
                "company": "Razorpay", "location": "Bangalore, India",
                "portal": "Razorpay Careers", "url": link})
        print(f"  [Razorpay]    {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Razorpay]    Error: {e}")
    return jobs


def scrape_zepto(keywords):
    jobs = []
    try:
        # Zepto uses Greenhouse
        url = "https://boards-api.greenhouse.io/v1/boards/zepto/jobs?content=true"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("jobs", []):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            location = job.get("location", {}).get("name", "India")
            link = job.get("absolute_url", "https://jobs.lever.co/zepto")
            jobs.append({"id": make_id("zepto", str(job.get("id",""))), "title": title,
                "company": "Zepto", "location": location,
                "portal": "Zepto Careers", "url": link})
        print(f"  [Zepto]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zepto]       Error: {e}")
    return jobs


def scrape_swiggy(keywords):
    jobs = []
    try:
        url = "https://careers.swiggy.com/api/jobs?department=Engineering"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        job_list = data if isinstance(data, list) else data.get("data", data.get("jobs", []))
        for job in job_list:
            title = job.get("title", job.get("name", ""))
            if not keyword_matches(title, keywords):
                continue
            link = job.get("url", job.get("link", "https://careers.swiggy.com"))
            if not link.startswith("http"):
                link = f"https://careers.swiggy.com{link}"
            jobs.append({"id": make_id("swiggy", title), "title": title,
                "company": "Swiggy", "location": "Bangalore, India",
                "portal": "Swiggy Careers", "url": link})
        print(f"  [Swiggy]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Swiggy]      Error: {e}")
    return jobs


def scrape_cred(keywords):
    jobs = []
    try:
        # CRED uses Lever
        url = "https://api.lever.co/v0/postings/dreamplug?mode=json"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data:
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            link = job.get("hostedUrl", "https://lever.co/dreamplug")
            loc  = job.get("categories", {}).get("location", "India")
            jobs.append({"id": make_id("cred", job.get("id",title)), "title": title,
                "company": "CRED", "location": loc,
                "portal": "CRED Careers", "url": link})
        print(f"  [CRED]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [CRED]        Error: {e}")
    return jobs


def scrape_meesho(keywords):
    jobs = []
    try:
        url = "https://meesho.io/jobs"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            title_el = a.find(["h2","h3","h4","span","p"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            href = a["href"]
            link = href if href.startswith("http") else f"https://meesho.io{href}"
            jobs.append({"id": make_id("meesho", title), "title": title,
                "company": "Meesho", "location": "Bangalore, India",
                "portal": "Meesho Careers", "url": link})
        print(f"  [Meesho]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Meesho]      Error: {e}")
    return jobs


def scrape_phonepe(keywords):
    jobs = []
    try:
        url = "https://boards-api.greenhouse.io/v1/boards/phonepe/jobs"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("jobs", []):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            link = job.get("absolute_url", "https://phonepe.com/en-in/careers.html")
            loc  = job.get("location", {}).get("name", "Bangalore")
            jobs.append({"id": make_id("phonepe", str(job.get("id",""))), "title": title,
                "company": "PhonePe", "location": loc,
                "portal": "PhonePe Careers", "url": link})
        print(f"  [PhonePe]     {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [PhonePe]     Error: {e}")
    return jobs


def scrape_groww(keywords):
    jobs = []
    try:
        url = "https://groww.in/careers"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            t = a.find(["h3","h4","span","p","div"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            href = a["href"]
            link = href if href.startswith("http") else f"https://groww.in{href}"
            jobs.append({"id": make_id("groww", title), "title": title,
                "company": "Groww", "location": "Bangalore, India",
                "portal": "Groww Careers", "url": link})
        print(f"  [Groww]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Groww]       Error: {e}")
    return jobs


def scrape_paytm(keywords):
    jobs = []
    try:
        url = "https://paytm.com/about-us/careers"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            t = a.find(["h3","h4","h5","span"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            href = a["href"]
            link = href if href.startswith("http") else f"https://paytm.com{href}"
            jobs.append({"id": make_id("paytm", title), "title": title,
                "company": "Paytm", "location": "Noida / Bangalore",
                "portal": "Paytm Careers", "url": link})
        print(f"  [Paytm]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Paytm]       Error: {e}")
    return jobs


def scrape_zomato(keywords):
    jobs = []
    try:
        # Zomato uses Lever
        url = "https://api.lever.co/v0/postings/zomato?mode=json"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data:
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            link = job.get("hostedUrl", "https://www.zomato.com/careers")
            loc  = job.get("categories", {}).get("location", "Gurugram")
            jobs.append({"id": make_id("zomato", job.get("id", title)), "title": title,
                "company": "Zomato", "location": loc,
                "portal": "Zomato Careers", "url": link})
        print(f"  [Zomato]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zomato]      Error: {e}")
    return jobs


def scrape_flipkart(keywords):
    jobs = []
    try:
        url = "https://www.flipkartcareers.com/#!/joblist"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all(["div","li"], class_=lambda c: c and "job" in (c or "").lower()):
            t = card.find(["h3","h4","a"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            a = card.find("a", href=True)
            href = a["href"] if a else ""
            link = href if href.startswith("http") else f"https://www.flipkartcareers.com{href}"
            jobs.append({"id": make_id("flipkart", title), "title": title,
                "company": "Flipkart", "location": "Bangalore, India",
                "portal": "Flipkart Careers", "url": link or "https://www.flipkartcareers.com"})
        print(f"  [Flipkart]    {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Flipkart]    Error: {e}")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  GLOBAL TECH COMPANIES (India offices)
# ─────────────────────────────────────────────────────────────────────

def scrape_google(keywords):
    jobs = []
    try:
        # Google Jobs API (public)
        url = (
            "https://careers.google.com/api/jobs/jobs-v1/search/"
            "?company=Google&company=YouTube&employment_type=FULL_TIME"
            "&hl=en_US&jlo=en_US&location=India&q="
            + "+".join(keywords[0].split() if keywords else ["engineer"])
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("jobs", [])[:10]:
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            job_id = job.get("job_id", title)
            link = f"https://careers.google.com/jobs/results/{job_id.split('/')[-1]}"
            locs = job.get("locations", [{}])
            loc  = locs[0].get("display", "India") if locs else "India"
            jobs.append({"id": make_id("google", job_id), "title": title,
                "company": "Google", "location": loc,
                "portal": "Google Careers", "url": link})
        print(f"  [Google]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Google]      Error: {e}")
    return jobs


def scrape_microsoft(keywords):
    jobs = []
    try:
        kw = "+".join(keywords[0].split() if keywords else ["engineer"])
        url = (
            f"https://jobs.careers.microsoft.com/global/en/search?"
            f"q={kw}&l=en_us&pg=1&pgSz=20&o=Relevance&flt=true"
        )
        r = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=15)
        data = r.json()
        for job in data.get("operationResult", {}).get("result", {}).get("jobs", []):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            loc = job.get("location", "India")
            if "india" not in loc.lower() and "hyderabad" not in loc.lower() \
               and "bangalore" not in loc.lower() and "noida" not in loc.lower():
                continue
            job_id = str(job.get("jobId", ""))
            link = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"
            jobs.append({"id": make_id("microsoft", job_id), "title": title,
                "company": "Microsoft", "location": loc,
                "portal": "Microsoft Careers", "url": link})
        print(f"  [Microsoft]   {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Microsoft]   Error: {e}")
    return jobs


def scrape_amazon(keywords):
    jobs = []
    try:
        kw = " ".join(keywords[0].split() if keywords else ["engineer"])
        url = (
            f"https://www.amazon.jobs/en/search.json?"
            f"base_query={requests.utils.quote(kw)}"
            f"&city=&country=IND&region=&job_type=Full-Time"
            f"&result_limit=20&sort=recent"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("jobs", []):
            title = job.get("title", "")
            if not keyword_matches(title, keywords):
                continue
            link = "https://www.amazon.jobs" + job.get("job_path", "/en/jobs")
            loc  = job.get("location", "India")
            jobs.append({"id": make_id("amazon", job.get("id", title)), "title": title,
                "company": "Amazon", "location": loc,
                "portal": "Amazon Jobs", "url": link})
        print(f"  [Amazon]      {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Amazon]      Error: {e}")
    return jobs


def scrape_meta(keywords):
    jobs = []
    try:
        kw = keywords[0] if keywords else "engineer"
        url = (
            f"https://www.metacareers.com/jobs?offices[0]=India&"
            f"q={requests.utils.quote(kw)}&sort_by_new=true"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", {"data-testid": lambda x: x and "job" in str(x).lower()}):
            title = a.get_text(strip=True)
            if not keyword_matches(title, keywords):
                continue
            href = a.get("href", "")
            link = f"https://www.metacareers.com{href}" if href.startswith("/") else href
            jobs.append({"id": make_id("meta", title), "title": title,
                "company": "Meta", "location": "India",
                "portal": "Meta Careers", "url": link})
        print(f"  [Meta]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Meta]        Error: {e}")
    return jobs


def scrape_adobe(keywords):
    jobs = []
    try:
        kw = keywords[0] if keywords else "engineer"
        url = (
            f"https://careers.adobe.com/us/en/search-results?"
            f"keywords={requests.utils.quote(kw)}&country=India"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("li", class_=lambda c: c and "job" in (c or "").lower()):
            t = card.find(["h2","h3","a"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if not keyword_matches(title, keywords):
                continue
            a = card.find("a", href=True)
            href = a["href"] if a else ""
            link = href if href.startswith("http") else f"https://careers.adobe.com{href}"
            jobs.append({"id": make_id("adobe", title), "title": title,
                "company": "Adobe", "location": "Noida / Bangalore, India",
                "portal": "Adobe Careers", "url": link})
        print(f"  [Adobe]       {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Adobe]       Error: {e}")
    return jobs


def scrape_atlassian(keywords):
    jobs = []
    try:
        url = "https://api.lever.co/v0/postings/atlassian?mode=json&location=India"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data:
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            link = job.get("hostedUrl", "https://www.atlassian.com/company/careers")
            loc  = job.get("categories", {}).get("location", "India")
            jobs.append({"id": make_id("atlassian", job.get("id", title)), "title": title,
                "company": "Atlassian", "location": loc,
                "portal": "Atlassian Careers", "url": link})
        print(f"  [Atlassian]   {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Atlassian]   Error: {e}")
    return jobs


def scrape_thoughtworks(keywords):
    jobs = []
    try:
        url = "https://www.thoughtworks.com/en-in/careers/jobs"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            t = a.find(["h3","h4","span","p"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            href = a["href"]
            link = href if href.startswith("http") else f"https://www.thoughtworks.com{href}"
            jobs.append({"id": make_id("thoughtworks", title), "title": title,
                "company": "ThoughtWorks", "location": "India",
                "portal": "ThoughtWorks Careers", "url": link})
        print(f"  [ThoughtWorks]{len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [ThoughtWorks] Error: {e}")
    return jobs


def scrape_freshworks(keywords):
    jobs = []
    try:
        url = "https://api.lever.co/v0/postings/freshworks?mode=json"
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data:
            title = job.get("text", "")
            if not keyword_matches(title, keywords):
                continue
            link = job.get("hostedUrl", "https://www.freshworks.com/company/careers/")
            loc  = job.get("categories", {}).get("location", "Chennai / India")
            jobs.append({"id": make_id("freshworks", job.get("id", title)), "title": title,
                "company": "Freshworks", "location": loc,
                "portal": "Freshworks Careers", "url": link})
        print(f"  [Freshworks]  {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Freshworks]  Error: {e}")
    return jobs


def scrape_zoho(keywords):
    jobs = []
    try:
        url = "https://careers.zohocorp.com/jobs/Careers"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all(["tr","div","li"], class_=lambda c: c and "job" in (c or "").lower()):
            t = row.find(["td","h3","h4","a","span"])
            if not t:
                continue
            title = t.get_text(strip=True)
            if len(title) < 5 or not keyword_matches(title, keywords):
                continue
            a = row.find("a", href=True)
            href = a["href"] if a else ""
            link = href if href.startswith("http") else f"https://careers.zohocorp.com{href}"
            jobs.append({"id": make_id("zoho", title), "title": title,
                "company": "Zoho", "location": "Chennai, India",
                "portal": "Zoho Careers", "url": link or "https://careers.zohocorp.com"})
        print(f"  [Zoho]        {len(jobs)} matching jobs")
    except Exception as e:
        print(f"  [Zoho]        Error: {e}")
    return jobs


# ─────────────────────────────────────────────────────────────────────
#  REGISTRY — maps company name → scraper function
# ─────────────────────────────────────────────────────────────────────

COMPANY_SCRAPERS = {
    # Indian companies
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
    # Global
    "google":       scrape_google,
    "microsoft":    scrape_microsoft,
    "amazon":       scrape_amazon,
    "meta":         scrape_meta,
    "adobe":        scrape_adobe,
    "atlassian":    scrape_atlassian,
}


def scrape_companies(keywords):
    """
    Called from job_monitor.py — scrapes all companies listed in
    config.py → COMPANY_TARGETS using keyword matching.
    Returns flat list of job dicts.
    """
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
                jobs = COMPANY_SCRAPERS[key](keywords)
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  [{company}] Error: {e}")
        else:
            print(f"  [{company}] ⚠️  No scraper found — check COMPANY_SCRAPERS in company_scrapers.py")

    return all_jobs