#!/usr/bin/env python3
import csv
import subprocess
import datetime
import os
import sys

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
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("++"):  # Ignore metadata lines
            parts = line[1:].split(",")
            if len(parts) == 2:
                hostname, status = parts[0].strip(), parts[1].strip().upper()
                if status not in ["ADD", "REMOVE"]:
                    log_error(f"{hostname},{status} #Please correct STATUS, it can be either ADD or REMOVE")
                else:
                    parsed_entries.append((hostname, status))
    return parsed_entries

def check_and_update_database(hostname, database_file):
    """Checks if a hostname exists in the database, updates it if not."""
    rows = read_csv(database_file)
    existing_ids = set(row[0] for row in rows[1:] if row)  # Skip header

    if hostname in existing_ids:
        return True  # Already exists

    empty_row_index = next((i for i, row in enumerate(rows) if row and row[0] == ''), None)
    
    if empty_row_index is not None:
        rows[empty_row_index][0] = hostname  # Assign new hostname
    else:
        log_error(f"{hostname}, no more conf files available.")
        return False

    write_csv(database_file, rows)
    return True

def apply_state(minion):
    """Applies the Salt state for the given minion."""
    try:
        result = subprocess.run(["sudo", "salt", minion, "state.apply", "check_confs"], capture_output=True, text=True)
        if "Succeeded:" in result.stdout and "Failed:    0" in result.stdout:
            log_access(f"{minion} conf files updated successfully.")
        else:
            log_error(f"{minion} state apply failed.")
    except Exception as e:
        log_error(f"Salt apply error for {minion}: {str(e)}")

def process_aws_entries():
    """Processes parsed entries for AWS CSV and AWS database."""
    filename = env.get("AWS_CSV")
    database_file = env.get("AWS_DATABASE")
    if filename and database_file:
        git_diff = get_git_diff(filename)
        if not git_diff:  # Exit silently if no diff found
            sys.exit(0)
            
        parsed_entries = parse_git_diff(git_diff)
        for hostname, status in parsed_entries:
            if status == "ADD":
                if check_and_update_database(hostname, database_file):
                    apply_state(hostname)

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