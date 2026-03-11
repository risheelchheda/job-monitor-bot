# 🚀 Run Your Bot 24/7 For Free (No Computer Needed)

Even when your laptop is off, the bot keeps running on Railway.app — a free cloud platform.
Setup takes about 10 minutes total.

---

## ✅ OPTION 1 — Railway.app (RECOMMENDED — Free forever for this use case)

### Step 1 — Install Git on your computer

**Windows:**
1. Go to https://git-scm.com/download/win
2. Download and install (click Next through everything)
3. Open Command Prompt and type: `git --version` — should show a version number

**Mac:**
1. Open Terminal
2. Type: `git --version` — Mac will auto-install it if missing

---

### Step 2 — Create a GitHub account

1. Go to https://github.com → Sign up (it's free)
2. Verify your email

---

### Step 3 — Upload your bot to GitHub

Open Command Prompt (Windows) or Terminal (Mac) and run these commands ONE BY ONE:

```bash
# Navigate to your job-monitor folder
cd path/to/job-monitor     # e.g. cd C:\Users\YourName\Downloads\job-monitor

# Set up git
git init
git add .
git commit -m "job monitor bot"

# Create a new repo on GitHub first at github.com/new
# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/job-monitor.git
git push -u origin main
```

💡 TIP: On GitHub.com, click the green "New" button to create a repo named "job-monitor"
   Then GitHub will show you the exact commands to paste — use those!

---

### Step 4 — Deploy on Railway

1. Go to https://railway.app → Sign up with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your **job-monitor** repository
5. Railway will detect it's a Python app automatically

---

### Step 5 — Add your secrets on Railway

1. In your Railway project, click your service
2. Click **"Variables"** tab
3. Add these one by one (click "Add Variable" for each):

```
EMAIL_USER     →  yourname@gmail.com
EMAIL_PASS     →  your16charapppassword
EMAIL_TO       →  yourname@gmail.com
ANTHROPIC_API_KEY  →  sk-ant-...
```

> ⚠️ IMPORTANT: You must also update config.py to read from environment variables.
> See the "Railway Config Update" section below.

---

### Step 6 — Update config.py to use Railway environment variables

Replace the values in your config.py with this pattern before pushing:

```python
import os

CONFIG = {
    "KEYWORDS": ["React Developer", "Frontend Developer"],
    "LOCATION": "Bangalore",
    "PORTALS": ["linkedin", "naukri", "indeed", "foundit"],
    "CHECK_INTERVAL_MINUTES": 20,

    # These are read from Railway environment variables (safe — no passwords in code)
    "EMAIL_USER": os.environ.get("EMAIL_USER", ""),
    "EMAIL_PASS": os.environ.get("EMAIL_PASS", ""),
    "EMAIL_TO":   os.environ.get("EMAIL_TO", ""),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "GENERATE_COVER_LETTERS": True,

    "USER_PROFILE": {
        "name": "Your Full Name",
        "target_role": "Senior React Developer",
        "experience_years": 4,
        "skills": ["React", "JavaScript", "TypeScript", "Node.js"],
    },
}
```

---

### Step 7 — Add a Procfile (tells Railway how to start your bot)

Create a file named exactly `Procfile` (no extension) in your job-monitor folder:

```
worker: python job_monitor.py
```

Then push to GitHub again:
```bash
git add .
git commit -m "add procfile and env config"
git push
```

Railway will automatically redeploy. Your bot is now running 24/7! 🎉

---

## ✅ OPTION 2 — PythonAnywhere (Even simpler, no Git needed)

1. Go to https://www.pythonanywhere.com → Sign up free
2. Go to **"Files"** tab → Upload all your job-monitor files
3. Go to **"Consoles"** tab → Start a Bash console
4. Run: `pip install -r requirements.txt --user`
5. Go to **"Tasks"** tab (free accounts get 1 always-on task)
6. Set command: `python /home/YOURUSERNAME/job_monitor.py`
7. Click Save — it runs forever!

---

## 📱 OPTION 3 — Old Android Phone (no internet cost)

If you have an old Android phone on WiFi:
1. Install **Termux** from F-Droid
2. Run: `pkg install python git`
3. Copy your files to the phone
4. Run: `python job_monitor.py &` (& keeps it running in background)

---

## 🔍 Checking your bot is running (Railway)

- Go to railway.app → your project → click **"Logs"** tab
- You should see scan logs every 20 minutes like:
  ```
  ========================================
  🔍 Scan at 14 Mar 2026  09:42:00 AM
  ========================================
  📌 'React Developer'
    [LinkedIn] 8 jobs for 'React Developer'
    [Naukri]   5 jobs for 'React Developer'
  ✅ 2 new job(s) | 26 total scanned
  ```

---

## ❓ Common Issues

| Problem | Fix |
|---|---|
| Gmail login fails | Use App Password not real password. 2FA must be ON. |
| 0 jobs found | Normal — LinkedIn rate limits. Bot retries in 20 min. |
| Railway stops after 30 days | Free tier has limits — upgrade to Hobby ($5/mo) or use PythonAnywhere |
| "Module not found" error | Run `pip install -r requirements.txt` first |
