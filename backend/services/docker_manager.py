import logging
import socket
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _qdrant_ready(host: str, port: int) -> bool:
    """Check if Qdrant REST API is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, socket.timeout):
        return False


def wait_for_qdrant(host: str = "localhost", port: int = 6333, timeout: int = 30) -> bool:
    """Poll TCP port until Qdrant is reachable or timeout expires."""
    logger.info(f"Waiting for Qdrant at {host}:{port} ...")
    start = time.time()
    while time.time() - start < timeout:
        if _qdrant_ready(host, port):
            logger.info("Qdrant is ready.")
            return True
        time.sleep(1)
    logger.error(f"Qdrant did not become ready within {timeout} seconds.")
    return False


def start_qdrant_container(project_root: Path) -> bool:
    """Run `docker compose up -d` from project_root and wait for Qdrant.

    Returns True if Qdrant is confirmed reachable, False otherwise.
    """
    compose_file = project_root / "docker-compose.yml"
    if not compose_file.exists():
        logger.warning(f"docker-compose.yml not found at {compose_file}; skipping auto-start.")
        return False

    # Check if Docker is available
    try:
        subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Docker Compose v2 not found. Ensure Docker Desktop is installed and running.")
        return False

    logger.info("Starting Qdrant container via docker compose ...")
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "qdrant"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        if result.returncode != 0:
            logger.error(f"docker compose up failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Failed to run docker compose: {e}")
        return False

    return wait_for_qdrant("localhost", 6333, timeout=30)
