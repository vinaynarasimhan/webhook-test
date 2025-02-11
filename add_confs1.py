import csv
import subprocess
import datetime
import os

# Load environment variables from env_dynamic file
def load_env(env_file="env_dynamic"):
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r") as file:
            for line in file:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
    return env_vars

env = load_env()

def ensure_log_file_exists(log_file):
    """Ensures that the log file exists before writing to it."""
    if not os.path.exists(log_file):
        with open(log_file, "w") as file:
            file.write("")  # Create an empty file

def log_error(message):
    """Logs an error message and ensures the log file exists."""
    log_file = env.get("ERROR_LOG", "error_log.txt")
    ensure_log_file_exists(log_file)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as log_file:
        log_file.write(f"{timestamp} - Error - {message}\n")

def log_access(message):
    """Logs an access message and ensures the log file exists."""
    log_file = env.get("ACCESS_LOG", "access_log.txt")
    ensure_log_file_exists(log_file)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as log_file:
        log_file.write(f"{timestamp} - {message}\n")

def commit_and_push_changes():
    """Commits and pushes changes if log files are modified."""
    dir_path = env.get("DIR", "./")
    branch = env.get("BRANCH", "main")
    try:
        subprocess.run(["git", "-C", dir_path, "add", "-A"], check=True)
        subprocess.run(["git", "-C", dir_path, "commit", "-m", f"Auto-commit: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        subprocess.run(["git", "-C", dir_path, "push", "origin", branch], check=True)
        log_access("Changes committed and pushed successfully.")
    except subprocess.CalledProcessError as e:
        log_error(f"Git commit/push failed: {str(e)}")

def main():
    process_aws_entries()
    commit_and_push_changes()

if __name__ == "__main__":
    main()
