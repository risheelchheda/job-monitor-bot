"""
config.py — Job Monitor Bot settings
Configured for: Risheel Chheda
"""

CONFIG = {

    # ─────────────────────────────────────
    # 🔍 WHAT JOBS TO SEARCH FOR
    # ─────────────────────────────────────

    "KEYWORDS": [
        "Software Developer",
        "Software Engineer",
        "Backend Developer",
        "Java Developer",
        "Spring Boot Developer",
        "Full Stack Developer",
        "Python Developer",
    ],

    # Change to "Bangalore", "Hyderabad", "Pune", "Remote" if open to relocate
    "LOCATION": "Mumbai",

    "PORTALS": ["linkedin", "naukri", "indeed", "foundit"],

    "CHECK_INTERVAL_MINUTES": 20,


    # ─────────────────────────────────────
    # 🏢 COMPANY CAREER PORTALS
    # ─────────────────────────────────────
    # Bot matches your KEYWORDS against job titles on each company's portal.
    #
    # Available companies:
    # Indian:   razorpay, zepto, swiggy, cred, meesho, phonepe,
    #           groww, paytm, zomato, flipkart, freshworks, zoho, thoughtworks
    # Global:   google, microsoft, amazon, meta, adobe, atlassian

    "COMPANY_TARGETS": [
        # Fintech / Payments (matches your NPCI background perfectly)
        "razorpay",
        "phonepe",
        "paytm",
        "cred",
        "groww",
        # Product companies
        "zepto",
        "swiggy",
        "zomato",
        "meesho",
        "flipkart",
        # Tech / Global
        "google",
        "microsoft",
        "amazon",
        "atlassian",
        "adobe",
        "freshworks",
        "thoughtworks",
        "zoho",
    ],


    # ─────────────────────────────────────
    # 📧 EMAIL NOTIFICATION (Gmail)
    # ─────────────────────────────────────
    #
    # HOW TO GET YOUR APP PASSWORD (2 minutes):
    # 1. Go to myaccount.google.com
    # 2. Click "Security" on the left sidebar
    # 3. Make sure "2-Step Verification" is ON
    # 4. In the search bar at top, type "App Passwords" and open it
    # 5. Select App = "Mail", Device = "Other" → type "JobBot" → Generate
    # 6. Copy the 16-character password shown (e.g. abcd efgh ijkl mnop)
    # 7. Paste it below WITHOUT spaces → "abcdefghijklmnop"

    "EMAIL_USER": "jobbot657@gmail.com",
    "EMAIL_PASS": "zgzx nkxb dtrm rpyl",
    "EMAIL_TO": "jobbot657@gmail.com",


    # ─────────────────────────────────────
    # 🤖 OLLAMA — FREE LOCAL AI
    # ─────────────────────────────────────
    #
    # SETUP (one-time):
    # 1. Download: https://ollama.com/download  (already installed!)
    # 2. Pull model: ollama pull llama3.2
    # 3. Ollama auto-starts on Windows — no need to run ollama serve

    "OLLAMA_URL":   "http://localhost:11434",
    "OLLAMA_MODEL": "llama3.2",
    "GENERATE_COVER_LETTERS": True,


    # ─────────────────────────────────────
    # 👤 YOUR PROFILE (used for cover letters)
    # ─────────────────────────────────────

    "USER_PROFILE": {
        "name":             "Risheel Chheda",
        "current_company":  "NPCI (National Payments Corporation of India)",
        "current_role":     "Software Developer",
        "target_role":      "Software Developer / Backend Engineer",
        "experience_years": 1.5,
        "education":        "B.Tech Electronics Engineering, VJTI Mumbai (CPI: 8.8/10)",
        "skills": [
            # Languages
            "Java", "Python", "JavaScript", "SQL", "C++",
            # Backend
            "Spring Boot", "Spring MVC", "Spring AI", "REST APIs",
            "Microservices", "Kafka", "Node.js", "Express.js", "LangChain",
            # Frontend
            "React.js", "HTML", "CSS",
            # Databases
            "PostgreSQL", "Cassandra", "MongoDB", "Redis", "ClickHouse",
            # DevOps & Cloud
            "Docker", "Kubernetes", "Jenkins", "GitLab CI/CD",
            "AWS", "Azure", "Prometheus", "Grafana",
            # Testing
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