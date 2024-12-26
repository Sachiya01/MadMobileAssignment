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

#This code was added for S3 addition and for S3 log rotation

def log_metrics_to_s3(bucket_name, file_name, new_data):
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')

        # Get the current time
        current_time = time.time()

        # Check if the file already exists in S3
        existing_data = []
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
            existing_data = json.loads(response['Body'].read().decode('utf-8'))
        except s3_client.exceptions.NoSuchKey:
            print("No existing file found in S3. Creating a new one.")

        # Filter out logs older than 60 seconds
        filtered_data = [
            log for log in existing_data
            if log.get("timestamp", 0) >= current_time - 60
        ]

        # Append the new data
        filtered_data.append(new_data)

        # Convert the updated data back to JSON
        updated_data = json.dumps(filtered_data, indent=4)

        # Upload the updated JSON file back to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=updated_data
        )
        print(f"Metrics successfully logged to S3: {bucket_name}/{file_name}")

    except Exception as e:
        print(f"Error logging metrics to S3: {e}") 


def log_metrics():    


    data = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
           
            "timestamp": time.time()
        }
    # Define the bucket and file path
    bucket_name = "testsachith"  # Replace with your bucket name
    file_name = "system_metrics.json"

    # Log to S3
    log_metrics_to_s3(bucket_name, file_name, data)
        
         # This is where I scripted to log files into a json called system_metrics
    with open("system_metrics.json", "a") as log_file:
            json.dump(data, log_file)
            log_file.write("\n")
        
    if data["cpu_usage"] > THRESHOLDS["cpu"]:
            send_email_alert(
                "CPU Usage Alert",
                f"CPU usage has exceeded the threshold! Current usage: {data['cpu_usage']}%"
            )
    if data["memory_usage"] > THRESHOLDS["memory"]:
            send_email_alert(
                "Memory Usage Alert",
                f"Memory usage has exceeded the threshold! Current usage: {data['memory_usage']}%"
            )
    if data["disk_usage"] > THRESHOLDS["disk"]:
            send_email_alert(
                "Disk Usage Alert",
                f"Disk usage has exceeded the threshold! Current usage: {data['disk_usage']}%"
            )
    
    time.sleep(10)

def publish_metric_to_cloudwatch(metric_name, value, unit="Percent"):
    """Publish a custom metric to AWS CloudWatch."""
    try:
        response = cloudwatch.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": [
                        {
                            "Name": "InstanceId",
                            "Value": INSTANCE_ID
                        }
                    ],
                    "Value": value,
                    "Unit": unit
                }
            ]
        )
        print(f"Published {metric_name}: {value} {unit} to CloudWatch")
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Failed to publish metric: {e}")