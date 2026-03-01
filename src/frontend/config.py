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


# HTTP server configuration
HTTP_SERVER_HOST = config.get("http_server_host", "localhost")
HTTP_SERVER_PORT = int(config.get("http_server_port", 8080))
BASE_URL = config.get("base_url")
CONNECTION_TIMEOUT_SECONDS = int(config.get("connection_timeout_seconds", 5))
HTTP_LISTEN_BACKLOG = int(config.get("http_listen_backlog", 128))


# IP blocklist configuration
RELOAD_BLOCKLIST_INTERVAL_SECONDS = int(
    config.get("reload_blocklist_interval_seconds", 1800))


# HTTPS certificate configuration
HTTPS_CERTIFICATE_PATH = config.get("https_certificate_path", "")
HTTPS_KEY_PATH = config.get("https_key_path", "")
