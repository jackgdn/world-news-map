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


# Frontend configuration
HTTP_SERVER_HOST = config.get("http_server_host", "0.0.0.0")
HTTP_SERVER_PORT = int(config.get("http_server_port", 8080))

# IP blocklist configuration
RELOAD_BLOCKLIST_INTERVAL_SECONDS = int(
    config.get("reload_blocklist_interval_seconds"))
