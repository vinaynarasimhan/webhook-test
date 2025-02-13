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

def get_git_diff(filename):
    """Gets the git diff for a specific file."""
    try:
        result = subprocess.run(["git", "diff", "HEAD@{1}", "--", filename], capture_output=True, text=True)
        return result.stdout.splitlines()
    except Exception as e:
        log_error(f"Git diff error: {str(e)}")
        return []

def parse_git_diff(diff_lines):
    """Parses the git diff output to extract new entries."""
    parsed_entries = []
    seen_hostnames = set()
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("++"):  # Ignore metadata lines
            parts = line[1:].split(",")
            if len(parts) == 2:
                hostname, status = parts[0].strip(), parts[1].strip().upper()
                if hostname in seen_hostnames:
                    log_error(f"Hostname '{hostname}' has appeared multiple times, please correct and reraise a request with correct status.")
                    continue
                seen_hostnames.add(hostname)
                if status not in ["ADD", "REMOVE"]:
                    log_error(f"Hostname '{hostname}' status is incorrect, please correct and reraise a request.")
                else:
                    parsed_entries.append((hostname, status))
    return parsed_entries

def write_log_file(log_file, entries):
    """Overwrites log file with new entries."""
    with open(log_file, "w") as file:
        for entry in entries:
            file.write(f"{entry}\n")

def process_aws_entries():
    """Processes parsed entries for AWS CSV and logs ADD/REMOVE hosts."""
    filename = env.get("AWS_CSV")
    hadd_log = env.get("AWS_HADD_LOG")
    hrem_log = env.get("AWS_HREM_LOG")
    dir_path = env.get("DIR", "./")
    branch = env.get("BRANCH", "main")
    
    if filename and hadd_log and hrem_log:
        git_diff = get_git_diff(filename)
        parsed_entries = parse_git_diff(git_diff)
        
        add_hosts = [hostname for hostname, status in parsed_entries if status == "ADD"]
        remove_hosts = [hostname for hostname, status in parsed_entries if status == "REMOVE"]
        
        if add_hosts:
            write_log_file(hadd_log, add_hosts)
        if remove_hosts:
            write_log_file(hrem_log, remove_hosts)
        
        # If no entries were written to the logs, commit and push changes
        if not add_hosts and not remove_hosts:
            try:
                subprocess.run(["git", "-C", dir_path, "add", "-A"], check=True)
                subprocess.run(["git", "-C", dir_path, "commit", "-m", f"Auto-commit: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                subprocess.run(["git", "-C", dir_path, "push", "origin", branch], check=True)
            except subprocess.CalledProcessError as e:
                log_error(f"Git commit/push failed: {str(e)}")

def main():
    process_aws_entries()

if __name__ == "__main__":
    main()
