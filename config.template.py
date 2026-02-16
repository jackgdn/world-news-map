# Request parameters
REQUEST_INTERVAL = 2
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3


# Language model API configuration
LANGUAGE_MODEL_BASE_URL = "your_base_url_here"  # Required
LANGUAGE_MODEL_NAME = "your_model_name_here"  # Required
LANGUAGE_MODEL_API_KEY = "your_api_key_here"  # Required
# Add any extra parameters required by your language model API. e.g. {"enable_enhancement": True}
# If you don't have any extra parameters, you can leave this as an empty dictionary.
LANGUAGE_MODEL_EXTRA_PARAMS = {}


# Logging configuration
LOG_LEVEL = "debug"  # Options: "debug", "info", "warning", "error", "critical"
LOG_DESCRIPTION_MAX_LENGTH = 15


# Cache configuration
# Required by Nominatim, which has a default cache expiration of 7 days.
CACHE_EXPIRATION_DAYS = 7
