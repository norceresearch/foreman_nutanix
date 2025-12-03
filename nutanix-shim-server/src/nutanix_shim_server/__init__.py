import sys
import subprocess

from fastapi_cli.cli import main as fastapi_main


def main() -> None:
    """Entry point that wraps fastapi-cli with the app path pre-configured."""
    if "--help" in sys.argv:
        msg = """
Useage: `nutanix-shim-server` to run server on http using port 8000, all options are passed to `fastapi run`.

        When used with `--ssl-certfile' and `--ssl-keyfile`, it will run with `uvicon` on https, all options will then be passed to `uvicorn`.
        """
        print(msg)
        return

    # If user supplied certificates, when we run with uvicorn
    if "--ssl-certfile" in sys.argv and "--ssl-keyfile" in sys.argv:
        cmd = [
            "uvicorn",
            "nutanix_shim_server.server:app",
            *sys.argv[1:],
        ]
        r = -1
        try:
            r = subprocess.check_call(cmd)
        except KeyboardInterrupt:
            pass
        sys.exit(r)
    else:
        sys.argv = [
            "fastapi",
            "run",
            "--entrypoint",
            "nutanix_shim_server.server:app",
            *sys.argv[1:],
        ]
        fastapi_main()
