import sys

from vrcutil.overlay import run_overlay_host


if __name__ == "__main__":
    raise SystemExit(run_overlay_host(sys.argv[1:]))
