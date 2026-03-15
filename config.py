SCRAPING_SOURCES = ["linkedin"]

LINKEDIN_SEARCH_QUERIES = [
    "digital marketing manager",
    "performance marketing manager",
    "digital marketing analyst",
    "marketing automation specialist",
    "growth marketing manager",
    "paid media manager",
    "SEO manager",
    "marketing data analyst",
]

LINKEDIN_LOCATION = "Hyderabad, Telangana, India"
LINKEDIN_GEO_ID   = "105556813"

LINKEDIN_JOB_POSTING_DATE = "r604800"
LINKEDIN_JOB_TYPE         = "F"
LINKEDIN_F_WT             = "1,3"

LINKEDIN_MAX_START = 100

CAREERS_FUTURE_SEARCH_QUERIES = []

CAREERS_FUTURE_SEARCH_CATEGORIES = [
    "Marketing / Public Relations"
]

CAREERS_FUTURE_SEARCH_EMPLOYMENT_TYPES = [
    "Permanent",
    "Full Time",
]

MAX_JOBS_PER_SEARCH = {
    "linkedin":       10,
    "careers_future": 10,
}
DEFAULT_MAX_JOBS_PER_SEARCH = 10

REQUEST_TIMEOUT     = 30
MAX_RETRIES         = 3
RETRY_DELAY_SECONDS = 30
