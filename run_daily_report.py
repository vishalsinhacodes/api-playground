import subprocess
import sys
import pathlib

# 1) Always run from the project directory so files resolve correctly.
ROOT = pathlib.Path(__file__).parent.resolve()

def run(cmd: list[str]) -> None:
    """
    Runs a child process and streams its output.
    - sys.executable ensures we use the current venv's Python.
    - check=True raises an error if the command fails (good for Task Scheduler).
    """
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)

if __name__ == "__main__":
    # 1) Refresh GitHub repos report
    run([sys.executable, "github_repos_to_csv.py"])
    
    # 2) Refresh Weather report
    run([sys.executable, "weather_current_to_csv.py"])
    
    # 3) Refresh Crypto report
    run([sys.executable, "crypto_prices_to_csv.py"])
    
    # 4) Email (currently sends repos.csv)
    run([sys.executable, "email_html_report.py"])
    print("\n✅ Daily HTML report (history + latest) completed.")
