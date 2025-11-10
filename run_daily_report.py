import subprocess
import sys

def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd, shell=False)
    
if __name__ == "__main__":
    # 1) Refresh repos.csv
    run([sys.executable, "github_repos_to_csv.py"])
    
    # 2) Email it
    run([sys.executable, "email_with_attachment.py"])