import subprocess
import sys
import os
from typing import List
import signal
import time

class ServerManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def start_servers(self):
        env = os.environ.copy()
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Gets the parent of dev/
        env["PYTHONPATH"] = f"{root_path}:{env.get('PYTHONPATH', '')}"


        servers = [
            ("local_server_ma:app", 8000),
            ("local_server_ra:app", 8001),
            ("local_server_te:app", 8002),
            ("local_server_pm:app", 8003),
        ]

        for module, port in servers:
            try:
                process = subprocess.Popen([
                    sys.executable,
                    "-m", "uvicorn",
                    module,
                    "--host", "0.0.0.0",
                    "--port", str(port),
                    "--reload"
                ], env=env)

                self.processes.append(process)
                print(f"Started server {module} on port {port}")

                # Small delay to prevent port conflicts
                time.sleep(2)

            except Exception as e:
                print(f"Failed to start {module} on port {port}: {str(e)}")

    def handle_shutdown(self, signum, frame):
        print("\nShutting down all servers...")
        self.shutdown()
        sys.exit(0)

    def shutdown(self):
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print(f"Error shutting down process: {str(e)}")

    def monitor(self):
        try:
            while True:
                for process in self.processes[:]:
                    if process.poll() is not None:
                        print(f"Process {process.pid} terminated unexpectedly")
                        self.processes.remove(process)

                if not self.processes:
                    print("All servers have stopped. Shutting down...")
                    break

                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

def main():
    manager = ServerManager()
    manager.start_servers()
    manager.monitor()

if __name__ == "__main__":
    main()
