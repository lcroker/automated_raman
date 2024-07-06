import sys
from pycromanager import Core, stop_headless

def shutdown_core():
    try:
        core = Core()
        core.reset()
        stop_headless(debug=True)
    except Exception as e:
        print(f"Error during shutdown: {e}", file=sys.stderr)
    finally:
        sys.exit(0)

if __name__ == "__main__":
    shutdown_core()
