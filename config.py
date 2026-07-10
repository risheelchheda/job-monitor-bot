"""
config.py  —  AWS Lambda version
- CHECK_INTERVAL_MINUTES is REMOVED — EventBridge cron triggers Lambda every 20 min
- Brevo is REMOVED — email is sent directly via Gmail SMTP
- All secrets are read from Lambda Environment Variables
  (set them in AWS Console → Lambda → Configuration → Environment Variables)
"""

import os

CONFIG = {

    # ─────────────────────────────────────
    # 🔍 JOB SEARCH SETTINGS
    # ─────────────────────────────────────

    "KEYWORDS": [
        "Software Developer",
        "Software Engineer",
        "Backend Developer",
        "Java Developer",
        "Spring Boot Developer",
        "Full Stack Developer",
    ],

    "LOCATION": ["Mumbai","Pune","Banglore"],

    "PORTALS": ["linkedin", "naukri", "indeed", "foundit"],

    # ─────────────────────────────────────
    # 🏢 COMPANY CAREER PORTALS
    # ─────────────────────────────────────

    "COMPANY_TARGETS": [
        "razorpay", "phonepe", "paytm", "cred", "groww",
        "zepto", "swiggy", "zomato", "meesho", "flipkart",
        "google", "microsoft", "amazon", "atlassian",
        "adobe", "freshworks", "thoughtworks", "zoho","Navi","Billdesk","Hsbc","Nium","jpmorgan","morganstanley","nielsen"
    ],

    # ─────────────────────────────────────
    # 📧 EMAIL  ← reads from Lambda env vars
    # ─────────────────────────────────────
    # Set these 3 variables in:
    # AWS Console → Lambda → Your Function → Configuration → Environment Variables
    #
    # EMAIL_USER  → your Gmail address         e.g. risheelchheda19@gmail.com
    # EMAIL_PASS  → Gmail App Password         (NOT your Gmail login password)
    #               Generate at: myaccount.google.com → Security → App Passwords
    # EMAIL_TO    → where to deliver alerts    e.g. risheelchheda19@gmail.com
    # ─────────────────────────────────────

    "EMAIL_USER": os.environ.get("EMAIL_USER", ""),
    "EMAIL_PASS": os.environ.get("EMAIL_PASS", ""),
    "EMAIL_TO":   os.environ.get("EMAIL_TO",   ""),

    # ─────────────────────────────────────
    # 🤖 OLLAMA — disabled on Lambda
    # Lambda has no local GPU/CPU for LLMs.
    # Cover letters are skipped entirely.
    # ─────────────────────────────────────

    "OLLAMA_URL":             "http://localhost:11434",
    "OLLAMA_MODEL":           "llama3.2",
    "GENERATE_COVER_LETTERS": False,  # must stay False on Lambda

    # ─────────────────────────────────────
    # 👤 YOUR PROFILE
    # ─────────────────────────────────────

    "USER_PROFILE": {
        "name":             "Risheel Chheda",
        "current_company":  "NPCI (National Payments Corporation of India)",
        "current_role":     "Software Developer",
        "target_role":      "Software Developer / Backend Engineer",
        "experience_years": 1.5,
        "education":        "B.Tech Electronics Engineering, VJTI Mumbai (CPI: 8.8/10)",
        "skills": [
            "Java", "Python", "JavaScript", "SQL", "C++",
            "Spring Boot", "Spring MVC", "Spring AI", "REST APIs",
            "Microservices", "Kafka", "Node.js", "Express.js", "LangChain",
            "React.js", "HTML", "CSS",
            "PostgreSQL", "Cassandra", "MongoDB", "Redis", "ClickHouse",
            "Docker", "Kubernetes", "Jenkins", "GitLab CI/CD",
            "AWS", "Azure", "Prometheus", "Grafana",
            "JUnit", "Mockito",
        ],
        "highlights": [
            "Led bank certification platform serving 100+ partner banks, reduced onboarding time by 50%",
            "Built internal support chatbot resolving 150+ weekly queries using Python and LangChain",
            "Optimized payment APIs to sub-500ms response times across 10,000+ daily transactions",
            "Winner — JPMorgan Chase Code for Good 2023",
            "Winner — NPCI Advanced Open Source Coding Challenge",
            "Winner — NPCI AI and ML Coding Challenge",
        ],
    },
}