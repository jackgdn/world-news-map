import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=Path(__file__).parent / "public", **kwargs)

    def log_message(self, format: str, *args) -> None:
        try:
            remote_addr = self.address_string()
            request_parts = self.requestline.split()
            method = request_parts[0] if len(request_parts) >= 1 else "-"
            path = request_parts[1] if len(request_parts) >= 2 else "-"
            protocol = request_parts[2] if len(request_parts) >= 3 else "-"
            status_code = args[3] if len(args) >= 4 else "-"
            bytes_sent = args[4] if len(args) >= 5 else "-"

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
    try:
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
