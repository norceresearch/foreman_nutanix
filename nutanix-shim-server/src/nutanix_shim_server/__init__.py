import sys

from fastapi_cli.cli import main as fastapi_main


def main() -> None:
    """Entry point that wraps fastapi-cli with the app path pre-configured."""
    # Insert 'run' command and app path, then append any user-provided args
    sys.argv = [
        "fastapi",
        "run",
        "--entrypoint",
        "nutanix_shim_server.server:app",
        *sys.argv[1:],
    ]
    fastapi_main()
