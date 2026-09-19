import subprocess
import sys
from pathlib import Path


def main():
    app_file = Path(__file__).resolve().with_name("insee_dashboard.py")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.headless",
        "true",
        "--server.port",
        "8501",
    ]
    print("Lancement du dashboard Streamlit...")
    print("URL locale : http://localhost:8501")
    print("Pour arrêter le serveur, appuie sur Ctrl+C dans ce terminal.")

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nArrêt du dashboard Streamlit.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
