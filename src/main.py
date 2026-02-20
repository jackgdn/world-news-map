import multiprocessing
import sys

from backend.run_backend import run_backend
from frontend.run_frontend import run_frontend


def main():
    backend_process = multiprocessing.Process(
        target=run_backend, name="BackendProcess")
    frontend_process = multiprocessing.Process(
        target=run_frontend, name="FrontendProcess")

    print("Starting backend service...")
    backend_process.start()
    print("Starting frontend service...")
    frontend_process.start()

    try:
        backend_process.join()
        frontend_process.join()
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, stopping all services...")
        if backend_process.is_alive():
            backend_process.terminate()
            backend_process.join()
        if frontend_process.is_alive():
            frontend_process.terminate()
            frontend_process.join()
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        backend_process.terminate() if backend_process.is_alive() else None
        frontend_process.terminate() if frontend_process.is_alive() else None
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
