# =============================================================================
# config.py — All scraper settings in one place
# Edit this file to change queries, filters, and limits.
# =============================================================================

# -----------------------------------------------------------------------------
# Which sources to scrape
# Options: "linkedin", "careers_future", or both
# -----------------------------------------------------------------------------
SCRAPING_SOURCES = ["linkedin", "careers_future"]

# -----------------------------------------------------------------------------
# LinkedIn — Search Queries
# Add or remove job titles/keywords as needed
# -----------------------------------------------------------------------------
LINKEDIN_SEARCH_QUERIES = [
    "data analyst",
    "python developer",
    "machine learning engineer",
    "data engineer",
    "business analyst",
]

# LinkedIn — Location Settings
LINKEDIN_LOCATION   = "Singapore"
LINKEDIN_GEO_ID     = "102454443"       # Singapore geo ID — change for other countries

# LinkedIn — Filters
LINKEDIN_JOB_POSTING_DATE = "r604800"   # Past 7 days (r86400 = 24h, r604800 = 7d, r2592000 = 30d)
LINKEDIN_JOB_TYPE         = "F"         # F=Full-time, P=Part-time, C=Contract, T=Temporary, I=Internship
LINKEDIN_F_WT             = "2"         # Work type: 1=On-site, 2=Remote, 3=Hybrid (comma-separate for multiple: "1,2,3")

# LinkedIn — Pagination
LINKEDIN_MAX_START = 100                # How deep to paginate (100 = up to 110 job IDs per query)

# -----------------------------------------------------------------------------
# Careers Future — Search Queries
# Add or remove job titles/keywords as needed
# -----------------------------------------------------------------------------
CAREERS_FUTURE_SEARCH_QUERIES = [
    "data analyst",
    "software engineer",
    "business analyst",
    "data engineer",
    "product manager",
]

# Careers Future — Filters
CAREERS_FUTURE_SEARCH_CATEGORIES = [
    "Information Technology"
    # Add more categories if needed, e.g. "Finance", "Engineering"
]

CAREERS_FUTURE_SEARCH_EMPLOYMENT_TYPES = [
    "Permanent",
    "Full Time",
    # "Part Time", "Contract", "Flexi-work"
]

# -----------------------------------------------------------------------------
# Job limits per query (prevents runaway scraping)
# Set to None for no limit
# -----------------------------------------------------------------------------
MAX_JOBS_PER_SEARCH = {
    "linkedin":       20,   # Max new jobs to fetch details for per query
    "careers_future": 30,   # Careers Future API is faster so can go higher
}
DEFAULT_MAX_JOBS_PER_SEARCH = 10        # Fallback if source not listed above

# -----------------------------------------------------------------------------
# HTTP request settings
# -----------------------------------------------------------------------------
REQUEST_TIMEOUT   = 30    # Seconds before a request times out
MAX_RETRIES       = 3     # Number of retries on 429 / network errors
RETRY_DELAY_SECONDS = 30  # Base wait time before retrying (jitter added on top)