import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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

    HTTP_LOG_FORMAT = "[HTTP] %(remote_addr)s - %(method)s %(path)s - %(status_code)s"

    def __init__(self, *args, **kwargs):
        self.public_dir = Path(__file__).parent.parent.parent / "public"
        super().__init__(*args, directory=self.public_dir, **kwargs)

    def log_message(self, format: str, *args) -> None:
        try:
            remote_addr = self.address_string()
            request_parts = self.requestline.split()
            method = request_parts[0] if len(request_parts) >= 1 else "-"
            path = request_parts[1] if len(request_parts) >= 2 else "-"
            status_code = args[0] if len(args) >= 1 else "-"

            log_data = {
                "remote_addr": remote_addr,
                "method": method,
                "path": path,
                "status_code": status_code,
            }

            logger.info(self.HTTP_LOG_FORMAT % log_data)
        except Exception as e:
            logger.error(f"Failed to log HTTP request: {e}", exc_info=True)


class WNMThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


def run_frontend() -> None:
    httpd = None
    try:
        server_address = (config.HTTP_SERVER_HOST, config.HTTP_SERVER_PORT)
        httpd = WNMThreadingHTTPServer(server_address, WNMHTTPRequestHandler)

        logger.info(f"Starting HTTP server at {config.BASE_URL}...")
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
