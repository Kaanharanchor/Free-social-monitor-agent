# Free-social-monitor-agent
This tool is to check the comments on public social profile and trigger an email if there is any negative comments found.

# Free Social Monitor Agent

This repository runs a free scheduled agent on GitHub Actions that:
 - Scrapes public pages for mentions of leaders.
 - Runs a Hugging Face sentiment model locally (free) to detect negative comments.
 - Sends email alerts via Gmail SMTP if negatives are found.

## Files
 - `monitor.py` : the main script (this file)
 - `requirements.txt` : Python dependencies
 - `.github/workflows/schedule.yml` : GitHub Actions workflow that runs the script on a schedule

## Setup (GitHub)
1. Create a new GitHub repository and push the files.
2. In your repository, go to **Settings -> Secrets & variables -> Actions -> Secrets** and add these secrets:
   - `EMAIL_FROM` : your Gmail address
   - `EMAIL_PASS` : an App Password from Gmail (NOT your real account password). See below.
   - `EMAIL_TO` : where alerts should be sent (can be same as EMAIL_FROM)
   - `LEADERS` : JSON array string of leader names, e.g. `["John Doe","Jane Smith"]`
   - `TARGET_URLS` : JSON array string of the public profile/post URLs to monitor, e.g. `["https://www.facebook.com/YourCompany","https://www.linkedin.com/company/your-company/"]`
   - Optionally `SENTIMENT_MODEL` to change the huggingface model

## Gmail app password
 - Enable 2FA on your Google account, then create an App Password for "Mail" and use it as `EMAIL_PASS`.
 - If you cannot use Gmail, change `send_email` in `monitor.py` to use another SMTP provider.

## How it works
 - The script fetches each TARGET_URL, extracts text snippets that mention any leader names, runs sentiment analysis, and emails you when negative sentiment is found.
 - GitHub Actions will run the script on the schedule you define in `.github/workflows/schedule.yml`.

## Limitations
 - HTML scraping is brittle and may not capture JS-rendered comments.
 - This is intentionally minimal and free — for production-grade reliability use official APIs or brand-monitoring services.

"""
