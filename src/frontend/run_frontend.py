import os
import re
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

try:
    from . import config
except ImportError:
    import config

try:
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    src_dir = os.path.dirname(backend_dir)
    if src_dir not in sys.path:
        sys.path.append(src_dir)
    from common.logger import frontend_logger as logger
except Exception as e:
    print(f"Error importing modules: {e}")
    raise


class WNMHTTPRequestHandler(SimpleHTTPRequestHandler):

    HTTP_LOG_FORMAT = "[HTTP] %(remote_addr)s - %(protocol)s %(method)s %(path)s - %(status_code)s %(bytes_sent)s"
    RELOAD_BLOCKLIST_INTERVAL_SECONDS = config.RELOAD_BLOCKLIST_INTERVAL_SECONDS

    # Shared set of IP blocklist
    banned_ips = set()
    banned_ips_lock = threading.Lock()
    banned_ips_file = Path(__file__).parent / "banned_ip.txt"

    # Allowed paths
    ALLOWED_PATHS = [
        r'^/$',                          # Root path
        r'^/index\.html$',               # index.html
        r'^/favicon\.ico$',              # favicon.ico
        r'^/news/[^/]+\.json$',          # /news/*.json
    ]

    def __init__(self, *args, **kwargs):
        self.public_dir = Path(__file__).parent / "public"
        super().__init__(*args, directory=self.public_dir, **kwargs)

    @classmethod
    def _read_banned_ips_from_file(cls) -> set:
        banned_ips = set()
        if not cls.banned_ips_file.exists():
            return banned_ips

        with open(cls.banned_ips_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ip = line.split('|')[0].strip()
                    if ip:
                        banned_ips.add(ip)
        return banned_ips

    @classmethod
    def load_banned_ips(cls) -> None:
        """
        Load banned IPs from file
        """
        try:
            latest_banned_ips = cls._read_banned_ips_from_file()
            with cls.banned_ips_lock:
                cls.banned_ips = latest_banned_ips
                logger.info(
                    f"Loaded {len(cls.banned_ips)} banned IPs from {cls.banned_ips_file}")
        except Exception as e:
            logger.error(f"Failed to load banned IPs: {e}", exc_info=True)

    @classmethod
    def reload_banned_ips(cls) -> None:
        """
        Reload banned IPs from file during runtime (file is source of truth)
        """
        try:
            latest_banned_ips = cls._read_banned_ips_from_file()
            with cls.banned_ips_lock:
                previous_count = len(cls.banned_ips)
                cls.banned_ips = latest_banned_ips
                current_count = len(cls.banned_ips)

            if previous_count != current_count:
                logger.info(
                    f"Reloaded banned IPs from file: {previous_count} -> {current_count}")
        except Exception as e:
            logger.error(f"Failed to reload banned IPs: {e}", exc_info=True)

    @classmethod
    def banned_ip_reload_worker(cls, stop_event: threading.Event) -> None:
        while not stop_event.wait(cls.RELOAD_BLOCKLIST_INTERVAL_SECONDS):
            cls.reload_banned_ips()

    @classmethod
    def save_banned_ip(cls, ip: str, reason: str = "") -> None:
        """
        Save a banned IP to the file
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cls.banned_ips_file, 'a', encoding='utf-8') as f:
                f.write(f"{ip} | {timestamp} | {reason}\n")
        except Exception as e:
            logger.error(
                f"Failed to save banned IP to file: {e}", exc_info=True)

    def is_ip_banned(self, ip: str) -> bool:
        with self.banned_ips_lock:
            return ip in self.banned_ips

    def ban_ip(self, ip: str, reason: str = "") -> None:
        with self.banned_ips_lock:
            if ip not in self.banned_ips:
                self.banned_ips.add(ip)
                logger.warning(f"IP banned: {ip} | Reason: {reason}")
                # Save to file
                self.save_banned_ip(ip, reason)

    def is_path_allowed(self, path: str) -> bool:
        """
        Check if the requested path is allowed
        """
        try:
            # Decode URL-encoded path and remove query parameters
            decoded_path = unquote(path.split('?')[0])

            # Standardize path
            if decoded_path == '':
                decoded_path = '/'

            # Check against allowed patterns
            for pattern in self.ALLOWED_PATHS:
                if re.match(pattern, decoded_path):
                    return True

            return False
        except Exception as e:
            logger.error(f"Path validation error for {path}: {e}")
            return False

    def send_head(self):
        """
        Hard guard: banned IP cannot access any file (including index.html)
        """
        client_ip = self.client_address[0]
        if self.is_ip_banned(client_ip):
            self.send_error(403, "Forbidden")
            return None
        return super().send_head()

    def send_response(self, code, message=None):
        """
        Override send_response
        """
        client_ip = self.client_address[0]

        # If the response code indicates an error, consider banning the IP
        if code > 400 and code != 404:
            logger.warning(
                f"High error code {code} from {client_ip} for {self.path}")
            self.ban_ip(client_ip, f"HTTP {code} error")

        super().send_response(code, message)

    def do_GET(self):
        client_ip = self.client_address[0]

        # Check if IP is banned
        if self.is_ip_banned(client_ip):
            logger.warning(f"Blocked request from banned IP: {client_ip}")
            self.send_error(403, "Forbidden")
            return

        # Check if path is allowed
        if not self.is_path_allowed(self.path):
            logger.warning(
                f"Unauthorized path access from {client_ip}: {self.path}")
            self.ban_ip(client_ip, f"Unauthorized path: {self.path}")
            self.send_error(403, "Forbidden")
            return

        # If everything is fine, proceed with the normal GET handling
        super().do_GET()

    def do_HEAD(self):
        """
        Check for banned IP and allowed paths before processing HEAD requests
        """
        client_ip = self.client_address[0]

        if self.is_ip_banned(client_ip):
            self.send_error(403, "Forbidden")
            return

        if not self.is_path_allowed(self.path):
            self.ban_ip(client_ip, f"Unauthorized path: {self.path}")
            self.send_error(403, "Forbidden")
            return

        super().do_HEAD()

    def do_POST(self):
        """
        Ban all POST requests
        """
        client_ip = self.client_address[0]
        logger.warning(f"POST request from {client_ip}, banning IP")
        self.ban_ip(client_ip, "POST method not allowed")
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        """
        Ban all PUT requests
        """
        client_ip = self.client_address[0]
        logger.warning(f"PUT request from {client_ip}, banning IP")
        self.ban_ip(client_ip, "PUT method not allowed")
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        """
        Ban all DELETE requests
        """
        client_ip = self.client_address[0]
        logger.warning(f"DELETE request from {client_ip}, banning IP")
        self.ban_ip(client_ip, "DELETE method not allowed")
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self):
        """
        Ban all OPTIONS requests
        """
        client_ip = self.client_address[0]
        logger.warning(f"OPTIONS request from {client_ip}, banning IP")
        self.ban_ip(client_ip, "OPTIONS method not allowed")
        self.send_error(405, "Method Not Allowed")

    def do_PATCH(self):
        """
        Ban all PATCH requests
        """
        client_ip = self.client_address[0]
        logger.warning(f"PATCH request from {client_ip}, banning IP")
        self.ban_ip(client_ip, "PATCH method not allowed")
        self.send_error(405, "Method Not Allowed")

    def log_message(self, format: str, *args) -> None:
        try:
            remote_addr = self.address_string()
            request_parts = self.requestline.split()
            method = request_parts[0] if len(request_parts) >= 1 else "-"
            path = request_parts[1] if len(request_parts) >= 2 else "-"
            protocol = request_parts[2] if len(request_parts) >= 3 else "-"
            status_code = args[0] if len(args) >= 1 else "-"
            bytes_sent = args[1] if len(args) >= 2 else "-"

            log_data = {
                "remote_addr": remote_addr,
                "method": method,
                "path": path,
                "protocol": protocol,
                "status_code": status_code,
                "bytes_sent": bytes_sent,
            }

            logger.info(self.HTTP_LOG_FORMAT % log_data)
        except Exception as e:
            logger.error(f"Failed to log HTTP request: {e}", exc_info=True)

    def log_error(self, format: str, *args) -> None:
        logger.error(f"HTTP error: {format % args}", exc_info=True)


def run_frontend() -> None:
    httpd = None
    reload_stop_event = threading.Event()
    reload_thread = None
    try:
        # Load banned IPs before starting the server
        WNMHTTPRequestHandler.load_banned_ips()

        reload_thread = threading.Thread(
            target=WNMHTTPRequestHandler.banned_ip_reload_worker,
            args=(reload_stop_event,),
            daemon=True,
            name="banned-ip-reloader",
        )
        reload_thread.start()

        server_address = (config.HTTP_SERVER_HOST, config.HTTP_SERVER_PORT)
        httpd = HTTPServer(server_address, WNMHTTPRequestHandler)
        logger.info(
            f"Starting HTTP server at http://{config.HTTP_SERVER_HOST}:{config.HTTP_SERVER_PORT}...")
        httpd.serve_forever()

    except KeyboardInterrupt:
        logger.warning(
            "Received KeyboardInterrupt (Ctrl+C), stopping HTTP server gracefully...")
        if httpd:
            httpd.shutdown()
            httpd.server_close()
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}", exc_info=True)
        raise
    finally:
        reload_stop_event.set()
        if reload_thread and reload_thread.is_alive():
            reload_thread.join(timeout=2)

        if httpd:
            httpd.server_close()
            logger.info("HTTP server socket closed successfully")


if __name__ == "__main__":
    try:
        run_frontend()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user, stopping backend gracefully...")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in frontend: {e}", exc_info=True)
        raise
