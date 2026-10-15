import os
import re
import json
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import feedparser
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def file_path(name):
    return os.path.join(ROOT, name)

def load_json(name, default):
    try:
        with open(file_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(name, data):
    target = file_path(name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temporary, target)

TOKEN = os.getenv("TG_TOKEN", "").strip()
ADMIN = os.getenv("TG_ADMIN", "").strip()
CHANNEL = os.getenv("TG_CHANNEL", "").strip()
TIMEOUT = max(4, min(int(os.getenv("SOURCE_TIMEOUT_SECONDS", "8")), 20))
WORKERS = max(2, min(int(os.getenv("SOURCE_WORKERS", "10")), 20))
MAX_REVIEW_ITEMS = 12
MAX_AGE_DAYS = 90

HEADERS = {
    "User-Agent": "GoResultHubExamMonitor/2.2 (+official-source monitor)",
    "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

EXAM_CONTEXT = re.compile(
    r"\b(exam|examination|entrance|competitive examination|civil services|"
    r"upsc|ias|ips|ssc|ibps|sbi|rrb|railway|nta|jee|neet|cuet|gate|"
    r"clerk|probationary officer|group d|assistant loco pilot|technician|"
    r"public service commission|board examination|ugc net|ctet|tet|"
    r"admit card|hall ticket|answer key|scorecard|merit list|exam result|"
    r"examination result|recruitment examination|prelims|mains)\b", re.I
)
SKIP = re.compile(
    r"\b(tender|quotation|procurement|vendor registration|privacy policy|"
    r"photo gallery|annual report|press release|media advisory|estate section|"
    r"classroom booking|associate professor|assistant professor|"
    r"professor appointment|guest faculty|school relocation|holiday list|"
    r"meeting notice)\b", re.I
)
RULES = [
    ("result", re.compile(r"\b(result declared|exam results?|examination results?|scorecards?|marks list|rank list|rank card)\b", re.I)),
    ("merit_list", re.compile(r"\b(merit list|final selection|selected candidates|qualified candidates|provisional selection|selection list|final panel|allotment list)\b", re.I)),
    ("cutoff", re.compile(r"\b(cut.?off marks?|cutoff marks?|qualifying marks?)\b", re.I)),
    ("admit_card", re.compile(r"\b(admit cards?|hall tickets?|call letters?|exam city intimation|city intimation slip)\b", re.I)),
    ("answer_key", re.compile(r"\b(answer keys?|response sheets?|objection tracker)\b", re.I)),
    ("exam_schedule", re.compile(r"\b(exam date|examination date|exam schedule|examination schedule|date sheet|exam calendar|exam postponement|exam rescheduled|examination postponed|examination rescheduled)\b", re.I)),
    ("notification", re.compile(r"\b(exam notification|examination notification|recruitment notification|recruitment advertisement|vacancy notification|information bulletin|application dates|registration opens|apply online|online application|application notice)\b", re.I)),
]
DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b"),
    re.compile(r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(20\d{2})\b", re.I),
]
MONTHS = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}

def host_allowed(url, allowed_hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            return False
        if isinstance(allowed_hosts, str):
            allowed_hosts = [allowed_hosts]
        return any(host == str(h).lower() or host.endswith("." + str(h).lower()) for h in allowed_hosts if h)
    except Exception:
        return False

def extract_title_date(text):
    for i, pattern in enumerate(DATE_PATTERNS):
        match = pattern.search(text or "")
        if not match:
            continue
        try:
            g = match.groups()
