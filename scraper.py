import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import json
import os
import config
import user_agents
from markdownify import markdownify as md


# --- Logging: stdout + file ---
for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scrape.log"),
    ]
)

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "").strip()
GITHUB_RUN_ID   = os.environ.get("GITHUB_RUN_ID", "local")


def send_to_n8n(jobs: list, source: str) -> None:
    if not N8N_WEBHOOK_URL:
        logging.error("[n8n] N8N_WEBHOOK_URL not set — skipping.")
        return
    if not jobs:
        logging.info(f"[n8n] No jobs to send for '{source}'.")
        return
    try:
        resp = requests.post(
            N8N_WEBHOOK_URL,
            json={"source": source, "run_id": GITHUB_RUN_ID, "job_count": len(jobs), "jobs": jobs},
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logging.info(f"[n8n] Sent {len(jobs)} job(s) [{source}] — HTTP {resp.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"[n8n] Failed: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def convert_html_to_markdown(html: str) -> str | None:
    if not html or not html.strip():
        return ""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
            tag.decompose()
        cleaned_html = str(soup)
        markdown_text = md(cleaned_html, heading_style="ATX", bullets="-", strip=['img'])
        lines = markdown_text.splitlines()
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            if not line.strip():
                if not prev_blank:
                    cleaned_lines.append('')
                prev_blank = True
            else:
                cleaned_lines.append(line)
                prev_blank = False
        return '\n'.join(cleaned_lines).strip() or ""
    except Exception as e:
        logging.error(f"HTML→Markdown error: {e}")
        return None


def _get_careers_future_company_name(job_item: dict) -> str | None:
    if not isinstance(job_item, dict):
        return None
    hc = job_item.get('hiringCompany')
    if isinstance(hc, dict) and hc.get('name'):
        return hc['name']
    pc = job_item.get('postedCompany')
    if isinstance(pc, dict) and pc.get('name'):
        return pc['name']
    return None


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------

def _fetch_linkedin_job_ids(search_query: str, location: str, limit: int = 10) -> list:
    job_ids_list = []
    start = 0
    max_start = config.LINKEDIN_MAX_START

    logging.info(f"LinkedIn Phase 1: scraping job IDs (stop at {limit} IDs)")

    while start <= max_start:
        if len(job_ids_list) >= limit:
            logging.info(f"Reached {limit} IDs — stopping pagination early.")
            break

        wt_param = f"&f_WT={config.LINKEDIN_F_WT}" if getattr(config, 'LINKEDIN_F_WT', '') else ""
        target_url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={search_query.replace(' ', '%20')}"
            f"&location={location}"
            f"&geoId={config.LINKEDIN_GEO_ID}"
            f"&f_TPR={config.LINKEDIN_JOB_POSTING_DATE}"
            f"&f_JT={config.LINKEDIN_JOB_TYPE}"
            f"{wt_param}"
            f"&start={start}"
        )

        if start > 0:
            time.sleep(random.uniform(2.0, 4.0))

        headers = {'User-Agent': random.choice(user_agents.USER_AGENTS)}
        logging.info(f"Scraping: {target_url}")

        res = None
        for attempt in range(config.MAX_RETRIES + 1):
            try:
                res = requests.get(target_url, headers=headers, timeout=config.REQUEST_TIMEOUT)
                res.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < config.MAX_RETRIES:
                    wait = config.RETRY_DELAY_SECONDS + random.uniform(0, 5)
                    logging.warning(f"429 — retrying in {wait:.1f}s (attempt {attempt+1})")
                    time.sleep(wait)
                    headers = {'User-Agent': random.choice(user_agents.USER_AGENTS)}
                else:
                    logging.error(f"HTTP error: {e}")
                    res = None
                    break
            except requests.exceptions.RequestException as e:
                logging.error(f"Request error: {e}")
                res = None
                break

        if res is None:
            logging.error("Failed to fetch page — stopping pagination.")
            break

        if not res.text:
            logging.info("Empty response — stopping.")
            break

        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('li')
        if not items:
            logging.info("No list items found — stopping.")
            break

        added = 0
        for item in items:
            base_card = item.find("div", {"class": "base-card"})
            urn = base_card.get('data-entity-urn') if base_card else None
            if urn and 'jobPosting:' in urn:
                try:
                    job_id = urn.split(":")[3]
                    if job_id not in job_ids_list:
                        job_ids_list.append(job_id)
                        added += 1
                except IndexError:
                    pass

        logging.info(f"start={start} → added {added} new IDs (total: {len(job_ids_list)})")

        if added == 0:
            break

        start += 10

    logging.info(f"LinkedIn Phase 1 done — {len(job_ids_list)} unique job IDs")
    return job_ids_list[:limit]


def _fetch_linkedin_job_details(job_id: str) -> dict | None:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    time.sleep(random.uniform(1.5, 3.0))
    headers = {'User-Agent': random.choice(user_agents.USER_AGENTS)}

    resp = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < config.MAX_RETRIES:
                wait = config.RETRY_DELAY_SECONDS + random.uniform(0, 5)
                logging.warning(f"429 for {job_id} — retrying in {wait:.1f}s")
                time.sleep(wait)
                headers = {'User-Agent': random.choice(user_agents.USER_AGENTS)}
            else:
                logging.error(f"HTTP error for {job_id}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error for {job_id}: {e}")
            return None

    if resp is None:
        return None

    try:
        soup = BeautifulSoup(resp.text, 'html.parser')
        details = {"job_id": job_id}

        # Company
        try:
            img = soup.find("div", {"class": "top-card-layout__card"}).find("a").find("img")
            details["company"] = img.get('alt', '').strip() if img else None
            if not details["company"]:
                link = soup.find("a", {"class": "topcard__org-name-link"})
                details["company"] = link.text.strip() if link else None
        except Exception:
            details["company"] = None

        # Title
        try:
            title_link = soup.find("div", {"class": "top-card-layout__entity-info"}).find("a")
            details["job_title"] = title_link.text.strip() if title_link else None
        except Exception:
            details["job_title"] = None

        # Level
        try:
            details["level"] = None
            for item in soup.find("ul", {"class": "description__job-criteria-list"}).find_all("li"):
                h = item.find("h3", {"class": "description__job-criteria-subheader"})
                if h and "Seniority level" in h.text:
                    span = item.find("span", {"class": "description__job-criteria-text"})
                    details["level"] = span.text.strip() if span else None
                    break
        except Exception:
            details["level"] = None

        # Location
        try:
            loc = soup.find("span", {"class": "topcard__flavor topcard__flavor--bullet"})
            details["location"] = loc.text.strip() if loc else None
        except Exception:
            details["location"] = None

        # Description
        try:
            desc_div = soup.find("div", {"class": "show-more-less-html__markup"})
            desc_html = str(desc_div) if desc_div else ""
            details["description"] = convert_html_to_markdown(desc_html) if desc_html.strip() else None
        except Exception:
            details["description"] = None

        details["provider"] = "linkedin"
        return details

    except Exception as e:
        logging.error(f"Error parsing details for {job_id}: {e}")
        return None


def process_linkedin_query(search_query: str, location: str, limit: int = 10) -> list:
    job_ids = _fetch_linkedin_job_ids(search_query, location, limit=limit)
    logging.info(f"Unique IDs scraped: {len(job_ids)}")

    results = []
    for job_id in job_ids:
        details = _fetch_linkedin_job_details(job_id)
        if details and details.get('description', '').strip():
            results.append(details)
        else:
            logging.warning(f"Skipping {job_id} — no description")

    logging.info(f"LinkedIn: {len(results)} jobs with full details")
    return results


# ---------------------------------------------------------------------------
# Careers Future
# ---------------------------------------------------------------------------

def _fetch_careers_future_jobs(search_query: str) -> list:
    suggestions_url = "https://api.mycareersfuture.gov.sg/v2/skills/suggestions"
    search_url_base = "https://api.mycareersfuture.gov.sg/v2/search"

    # Get skill UUIDs
    skill_uuids = []
    try:
        r = requests.post(suggestions_url, data={'jobTitle': search_query}, timeout=config.REQUEST_TIMEOUT)
        r.raise_for_status()
        skill_uuids = [s['uuid'] for s in r.json().get('skills', []) if 'uuid' in s]
        logging.info(f"CF: {len(skill_uuids)} skill UUIDs for '{search_query}'")
    except Exception as e:
        logging.error(f"CF skill suggestions error: {e}")
        return []

    # Paginate job search
    all_jobs = []
    current_url = f"{search_url_base}?limit=100&page=0"
    payload = {
        'sessionId': "",
        'search': search_query,
        'categories': config.CAREERS_FUTURE_SEARCH_CATEGORIES,
        'employmentTypes': config.CAREERS_FUTURE_SEARCH_EMPLOYMENT_TYPES,
        'postingCompany': [],
        'sortBy': ["new_posting_date"],
        'skillUuids': skill_uuids,
    }

    page = 0
    while current_url:
        try:
            r = requests.post(current_url, json=payload, timeout=config.REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            page_jobs = data.get('results', [])
            all_jobs.extend(page_jobs)
            logging.info(f"CF page {page}: {len(page_jobs)} jobs (total: {len(all_jobs)})")
            next_info = data.get("_links", {}).get("next", {})
            current_url = next_info.get("href") if next_info else None
            page += 1
        except Exception as e:
            logging.error(f"CF search error on page {page}: {e}")
            break

    logging.info(f"CF: {len(all_jobs)} total job items for '{search_query}'")
    return all_jobs


def _fetch_careers_future_job_details(job_id: str) -> dict | None:
    if not job_id:
        return None

    url = f"https://api.mycareersfuture.gov.sg/v2/jobs/{job_id}"
    try:
        r = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        raw_html = data.get('description', '')
        description = convert_html_to_markdown(raw_html) if raw_html.strip() else None

        return {
            'job_id':      data.get('uuid'),
            'company':     _get_careers_future_company_name(data),
            'job_title':   data.get('title'),
            'location':    'Singapore',
            'level':       data.get('positionLevels', [{'position': 'Not applicable'}])[0].get('position', 'Not applicable'),
            'provider':    'careers_future',
            'description': description,
            'posted_at':   data.get('metadata', {}).get('createdAt', ''),
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logging.warning(f"CF job {job_id} not found (404)")
        else:
            logging.error(f"CF HTTP error for {job_id}: {e}")
    except Exception as e:
        logging.error(f"CF error for {job_id}: {e}")

    return None


def process_careers_future_query(search_query: str, limit: int = None) -> list:
    job_items = _fetch_careers_future_jobs(search_query)
    if not job_items:
        return []

    job_ids = [str(item.get('uuid')) for item in job_items if item.get('uuid')]
    job_ids = list(dict.fromkeys(job_ids))  # deduplicate, preserve order

    if limit:
        job_ids = job_ids[:limit]
        logging.info(f"CF: capped to {limit} IDs")

    results = []
    for job_id in job_ids:
        details = _fetch_careers_future_job_details(job_id)
        if details and details.get('description', '').strip():
            results.append(details)
        else:
            logging.warning(f"CF: skipping {job_id} — no description")

    logging.info(f"CF: {len(results)} jobs with full details")
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    total_sent = 0
    errors = []

    LOCATION_FILTER = getattr(config, 'LOCATION_FILTER', [])

    def location_allowed(job: dict) -> bool:
        if not LOCATION_FILTER:
            return True
        loc = (job.get('location') or '').lower()
        return any(f.lower() in loc for f in LOCATION_FILTER)

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    if "linkedin" in config.SCRAPING_SOURCES:
        logging.info("=== LinkedIn scraping started ===")
        max_jobs = config.MAX_JOBS_PER_SEARCH.get(
            "linkedin", getattr(config, "DEFAULT_MAX_JOBS_PER_SEARCH", 10)
        )
        batch = []

        for query in config.LINKEDIN_SEARCH_QUERIES:
            logging.info(f"Query: '{query}'")
            try:
                jobs = process_linkedin_query(query, config.LINKEDIN_LOCATION, limit=max_jobs)
                if LOCATION_FILTER:
                    before = len(jobs)
                    for j in jobs:
                        loc = (j.get('location') or 'NONE')
                        allowed = location_allowed(j)
                        logging.info(f"  [{('PASS' if allowed else 'DROP')}] {j.get('company','?')} | {j.get('job_title','?')} | location='{loc}'")
                    jobs = [j for j in jobs if location_allowed(j)]
                    max_after_filter = getattr(config, 'LOCATION_FILTER_MAX', 10)
                    jobs = jobs[:max_after_filter]
                    logging.info(f"Location filter: {before} → {len(jobs)} job(s)")
                batch.extend(jobs)
                logging.info(f"'{query}' → {len(jobs)} job(s)")
            except Exception as e:
                msg = f"LinkedIn '{query}' failed: {e}"
                logging.error(msg)
                errors.append(msg)

        if batch:
            send_to_n8n(batch, source="linkedin")
            total_sent += len(batch)
        logging.info(f"=== LinkedIn done: {len(batch)} job(s) sent to n8n ===")

    # ── Careers Future ────────────────────────────────────────────────────────
    if "careers_future" in config.SCRAPING_SOURCES:
        logging.info("=== Careers Future scraping started ===")
        max_jobs = config.MAX_JOBS_PER_SEARCH.get(
            "careers_future", getattr(config, "DEFAULT_MAX_JOBS_PER_SEARCH", 10)
        )
        batch = []

        for query in config.CAREERS_FUTURE_SEARCH_QUERIES:
            logging.info(f"Query: '{query}'")
            try:
                jobs = process_careers_future_query(query, limit=max_jobs)
                batch.extend(jobs)
                logging.info(f"'{query}' → {len(jobs)} job(s)")
            except Exception as e:
                msg = f"CF '{query}' failed: {e}"
                logging.error(msg)
                errors.append(msg)

        if batch:
            send_to_n8n(batch, source="careers_future")
            total_sent += len(batch)
        logging.info(f"=== Careers Future done: {len(batch)} job(s) sent to n8n ===")

    logging.info(f"=== All done. Total jobs sent to n8n: {total_sent} ===")
