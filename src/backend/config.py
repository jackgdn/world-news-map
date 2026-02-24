import os
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
CONTACT_INFO = os.getenv("CONTACT_INFO")


# Language model API configuration
LANGUAGE_MODEL_BASE_URL = os.getenv("LANGUAGE_MODEL_BASE_URL")
LANGUAGE_MODEL_NAME = os.getenv("LANGUAGE_MODEL_NAME")
LANGUAGE_MODEL_API_KEY = os.getenv("LANGUAGE_MODEL_API_KEY")
LANGUAGE_MODEL_EXTRA_PARAMS = config.get("language_model_extra_params", dict())


# Logging configuration
LOG_DESCRIPTION_MAX_LENGTH = int(config.get("log_description_max_length", 15))


# Cache configuration
CACHE_EXPIRATION_DAYS = int(config.get("cache_expiration_days", 7))


# Update scheduling
UPDATE_INTERVAL_HOURS = int(config.get("update_interval_hours", 12))


# Frontend configuration
BASE_URL = os.getenv("BASE_URL")
