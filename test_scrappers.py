from job_monitor import scrape_naukri, scrape_indeed, scrape_foundit
from company_scrapers import (
    scrape_razorpay, scrape_groww, scrape_zepto,
    scrape_swiggy, scrape_zomato, scrape_meesho,
    scrape_flipkart, scrape_atlassian, scrape_adobe,
    scrape_freshworks, scrape_zoho, scrape_microsoft
)

keywords = ["Software Developer", "Java Developer", "Backend Developer"]

print("\n=== JOB PORTALS ===")
print(f"Naukri:  {len(scrape_naukri('Software Developer', 'Mumbai'))} jobs")
print(f"Indeed:  {len(scrape_indeed('Software Developer', 'Mumbai'))} jobs")
print(f"Foundit: {len(scrape_foundit('Software Developer', 'Mumbai'))} jobs")

print("\n=== COMPANY SCRAPERS ===")
print(f"Razorpay:   {len(scrape_razorpay(keywords))} jobs")
print(f"Groww:      {len(scrape_groww(keywords))} jobs")
print(f"Zepto:      {len(scrape_zepto(keywords))} jobs")
print(f"Swiggy:     {len(scrape_swiggy(keywords))} jobs")
print(f"Zomato:     {len(scrape_zomato(keywords))} jobs")
print(f"Meesho:     {len(scrape_meesho(keywords))} jobs")
print(f"Flipkart:   {len(scrape_flipkart(keywords))} jobs")
print(f"Atlassian:  {len(scrape_atlassian(keywords))} jobs")
print(f"Adobe:      {len(scrape_adobe(keywords))} jobs")
print(f"Freshworks: {len(scrape_freshworks(keywords))} jobs")
print(f"Zoho:       {len(scrape_zoho(keywords))} jobs")
print(f"Microsoft:  {len(scrape_microsoft(keywords))} jobs")