import os
import re
import json
import time
import smtplib
import logging
from email.mime.text import MIMEText
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from transformers import pipeline

# ---------------- CONFIG ----------------
# Provide leader names and target URLs via environment variables (set as GitHub Secrets)
# - LEADERS: JSON array string, e.g. '["John Doe","Jane Smith"]'
# - TARGET_URLS: JSON array string, e.g. '["https://www.facebook.com/...","https://www.linkedin.com/..."]'
# - EMAIL_FROM, EMAIL_PASS, EMAIL_TO

LEADERS = json.loads(os.getenv("LEADERS", "[]"))
TARGET_URLS = json.loads(os.getenv("TARGET_URLS", "[]"))
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# Operational options
MIN_LEADER_MATCH = 1   # how many leader name tokens must match in a snippet
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")
MIN_NEGATIVE_SCORE = 0.6  # for models that return scores: require >= this to call it negative

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Helpers ----------------

def fetch_html(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SocialMonitor/1.0; +https://example.com)"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""


def extract_candidate_snippets(html: str, leaders: List[str]) -> List[Dict]:
    """
    Very permissive extraction: collect text blocks (paragraphs/divs/spans) and keep those
    that contain any leader name (case-insensitive). Return list of dicts {text, context}
    """
    soup = BeautifulSoup(html, "html.parser")

    # collect visible text nodes from common tags
    tags = soup.find_all(["p", "span", "div", "li", "article", "blockquote"])
    snippets = []
    leader_tokens = [l.lower() for l in leaders]

    for t in tags:
        text = t.get_text(separator=" ", strip=True)
        if not text or len(text) < 15:
            continue
        txt_low = text.lower()
        # quick check: must contain at least one leader name
        if any(lt in txt_low for lt in leader_tokens):
            # try to trim to sentence(s) containing leader names
            sentences = re.split(r"(?<=[.!?]) +", text)
            for s in sentences:
                s_low = s.lower()
                if any(lt in s_low for lt in leader_tokens):
                    snippets.append({"text": s.strip(), "context": text.strip()})
    # fallback: if nothing found in tags, try full-page text search
    if not snippets:
        full = soup.get_text(separator=" ", strip=True)
        for lt in leader_tokens:
            if lt in full.lower():
                # grab surrounding window around first occurrence
                idx = full.lower().find(lt)
                start = max(0, idx - 200)
                end = min(len(full), idx + 200)
                snippets.append({"text": full[start:end].strip(), "context": full[start:end].strip()})
    return snippets


def leader_matched(snippet: str, leaders: List[str]) -> str:
    """
    Return the matched leader name (first match) or empty.
    Uses case-insensitive substring matching.
    """
    s = snippet.lower()
    for l in leaders:
        if l.lower() in s:
            return l
    return ""


def send_email(subject: str, body: str) -> bool:
    if not (EMAIL_FROM and EMAIL_PASS and EMAIL_TO):
        logger.error("Email credentials not set. Skipping email.")
        return False
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        server.quit()
        logger.info("Email sent")
        return True
    except Exception as e:
        logger.exception(f"Failed to send email: {e}")
        return False


# ---------------- Main ----------------

def main():
    if not LEADERS or not TARGET_URLS:
        logger.error("Please set LEADERS and TARGET_URLS environment variables (see README).")
        return

    logger.info(f"Loading sentiment model: {SENTIMENT_MODEL}")
    sentiment = pipeline("sentiment-analysis", model=SENTIMENT_MODEL)

    alerts = []

    for url in TARGET_URLS:
        logger.info(f"Checking {url}")
        html = fetch_html(url)
        if not html:
            continue
        snippets = extract_candidate_snippets(html, LEADERS)
        logger.info(f"Found {len(snippets)} candidate snippets on {url}")

        for sn in snippets:
            text = sn['text']
            matched = leader_matched(text, LEADERS)
            if not matched:
                continue
            # analyze sentiment
            try:
                res = sentiment(text[:512])  # limit length
            except Exception as e:
                logger.exception(f"Sentiment call failed: {e}")
                continue
            # res is like [{'label': 'NEGATIVE', 'score': 0.98}]
            label = res[0].get('label')
            score = res[0].get('score', 0.0)
            logger.info(f"Snippet for {matched}: label={label}, score={score:.2f}")

            is_negative = False
            # models sometimes label as NEGATIVE or LABEL_0 depending on model
            if isinstance(label, str) and ('neg' in label.lower()):
                if score >= MIN_NEGATIVE_SCORE:
                    is_negative = True
            # handle other model label names
            if label in ("LABEL_0",) and score >= MIN_NEGATIVE_SCORE:
                is_negative = True

            if is_negative:
                alert = {
                    "leader": matched,
                    "text": text,
                    "context": sn.get('context', ''),
                    "url": url,
                    "score": score,
                }
                alerts.append(alert)

    # dedupe alerts (by text+url)
    seen = set()
    final_alerts = []
    for a in alerts:
        key = (a['leader'], a['text'], a['url'])
        if key in seen:
            continue
        seen.add(key)
        final_alerts.append(a)

    if final_alerts:
        body_lines = []
        for a in final_alerts:
            body_lines.append(f"Leader: {a['leader']}")
            body_lines.append(f"Score: {a['score']}")
            body_lines.append(f"Comment snippet: {a['text']}")
            body_lines.append(f"Post URL: {a['url']}")
            body_lines.append("---")
        body = "\n".join(body_lines)
        subj = f"Negative comments detected ({len(final_alerts)})"
        send_email(subj, body)
    else:
        logger.info("No negative comments found.")


if __name__ == '__main__':
    main()
