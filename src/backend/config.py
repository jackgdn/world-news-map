from pathlib import Path

import yaml

current_file = Path(__file__).resolve()
backend_dir = current_file.parent
src_dir = backend_dir.parent
project_root = src_dir.parent
config_yaml_path = project_root / "config.yaml"

try:
    with open(config_yaml_path, "r") as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"Error loading config.yaml: {e}")
    raise


# Request parameters
REQUEST_INTERVAL = int(config.get("request_interval", 1))
REQUEST_TIMEOUT = int(config.get("request_timeout", 10))
MAX_RETRIES = int(config.get("max_retries", 3))
CONTACT_INFO = config.get("contact_info", "")


# Language model API configuration
LANGUAGE_MODEL_BASE_URL = config.get("language_model_base_url")
LANGUAGE_MODEL_NAME = config.get("language_model_name")
LANGUAGE_MODEL_API_KEY = config.get("language_model_api_key")
LANGUAGE_MODEL_EXTRA_PARAMS = config.get("language_model_extra_params", dict())


# Logging configuration
LOG_DESCRIPTION_MAX_LENGTH = int(config.get("log_description_max_length", 15))


# Cache configuration
CACHE_EXPIRATION_DAYS = int(config.get("cache_expiration_days", 7))


# Update scheduling
UPDATE_INTERVAL_HOURS = int(config.get("update_interval_hours", 12))
