# This is not a script that is meant to work.
# This script shows the part that should be added to MonitoringSetup in order to enable the option enhancement of Log Rotation

def delete_old_logs():
    """Delete log entries older than 1 minute from the log file."""
    try:
        current_time = time.time()
        updated_logs = []
        logs_deleted = False

        # Read existing log entries
        if os.path.exists("system_metrics.json"):
            with open("system_metrics.json", "r") as log_file:
                for line in log_file:
                    log_entry = json.loads(line)
                    if current_time - log_entry["timestamp"] <= 60:
                        updated_logs.append(log_entry)
                    else:
                        logs_deleted = True

        # Write back only recent log entries
        with open("system_metrics.json", "w") as log_file:
            for entry in updated_logs:
                json.dump(entry, log_file)
                log_file.write("\n")

        if logs_deleted:
            print("Old log entries deleted.")
    except Exception as e:
        print(f"Error deleting old logs: {e}")