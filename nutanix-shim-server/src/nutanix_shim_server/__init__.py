import sys

from fastapi_cli.cli import main as fastapi_main

from nutanix_shim_server import server


def main() -> None:
    """Entry point that wraps fastapi-cli with the app path pre-configured."""
    if "--help" in sys.argv:
        msg = f"""
Usage: `nutanix-shim-server` to run server on port 8000 (default)
with http, all options are passed to `fastapi run`.

When used with `--ssl-certfile' and `--ssl-keyfile`, it will run 
with `uvicorn` on https, all options will then be passed to `uvicorn`.

Available environment variables and their current values:
{server.Context.state_str()}
        """
        print(msg)
        return

    # If user supplied certificates, when we run with uvicorn
    if "--ssl-certfile" in sys.argv and "--ssl-keyfile" in sys.argv:
        # Make host default to same as fastapi, both default to port 8000
        if "--host" not in sys.argv:
            sys.argv.extend(["--host", "0.0.0.0"])

        try:
            import uvicorn
        except ImportError:
            sys.stderr.write("`uvicorn` not installed")
            sys.exit(-1)
        else:
            sys.argv = ["uvicorn", "nutanix_shim_server.server:app", *sys.argv[1:]]
            uvicorn.main()
    else:
        sys.argv = [
            "fastapi",
            "run",
            "--entrypoint",
            "nutanix_shim_server.server:app",
            *sys.argv[1:],
        ]
        fastapi_main()
