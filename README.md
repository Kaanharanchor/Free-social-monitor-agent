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

##

## How it works
 - The script fetches each TARGET_URL, extracts text snippets that mention any leader names, runs sentiment analysis, and emails you when negative sentiment is found.
 - GitHub Actions will run the script on the schedule you define in `.github/workflows/schedule.yml`.

## Limitations
 - HTML scraping is brittle and may not capture JS-rendered comments.
 - This is intentionally minimal and free — for production-grade reliability use official APIs or brand-monitoring services.

"""
