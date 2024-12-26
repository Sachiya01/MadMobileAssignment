import psutil
import time
import boto3
import subprocess
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

# Configuration
CHECK_INTERVAL = 10  # Seconds between metric checks
CLOUDWATCH_NAMESPACE = "CustomMetrics"  # CloudWatch namespace for custom metrics
INSTANCE_ID = "i-0d02b46bae51d830d"  # Replace with the instance ID of the monitored EC2
PING_HOST = "8.8.8.8"  # Host to ping for latency measurement ( I'm using the primary DNS server for Google DNS for testing purposes)
SMTP_SERVER = "smtp.gmail.com"  # gmail smtp server
SMTP_PORT = 587
EMAIL_ADDRESS = "sachithliyanage07@gmail.com"  
EMAIL_PASSWORD = "eoyq gxrc jbcd raza"  # Have to add a app-specific password
ALERT_RECIPIENT = "sachithliyanage07+1@gmail.com"  
# Define thresholds for performance metrics
THRESHOLDS = {
    "cpu": 75,
    "memory": 75,
    "disk": 60,  # Disk usage threshold in percentage
    "network_latency": 100  # Network latency threshold in milliseconds
}

# I created a stop file for emergency stop cases
STOP_FILE = "stop.flag"

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')

def send_email_alert(subject, message):
    """
    Sends an email alert with the specified subject and message.
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = ALERT_RECIPIENT
        msg["Subject"] = subject

       
        msg.attach(MIMEText(message, "I'm adding an example body"))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Email alert sent to {ALERT_RECIPIENT}")
    except Exception as e:
        print(f"Error sending email: {e}")

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

def monitor_system():
    """Monitor system metrics: CPU, memory, disk usage, and network latency."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    disk_usage = psutil.disk_usage('/').percent
    network_latency = measure_latency(PING_HOST)
    return cpu_usage, memory_usage, disk_usage, network_latency

def measure_latency(host):
    """Measure network latency to a specified host using the ping command on Windows."""
    try:

        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", host],  # Adjusted for Windows. For Linux I can use -c
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in result.stdout.splitlines():
            if "time=" in line:  
                latency = float(line.split("time=")[1].split("ms")[0].strip())
                return latency
    except Exception as e:
        print(f"Error measuring latency: {e}")
    return None

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

def main():
    print("Monitoring started. To stop monitoring, create a file named 'stop.flag'.")

    while True:
        # Check if stop file exists
        if os.path.exists(STOP_FILE):
            print("Stop file detected. Terminating monitoring.")
            break
        log_metrics()
        delete_old_logs()
        cpu_usage, memory_usage, disk_usage, network_latency = monitor_system()
        print(f"CPU: {cpu_usage}%, Memory: {memory_usage}%, Disk: {disk_usage}%, Latency: {network_latency} ms")

        # Publish metrics to CloudWatch
        publish_metric_to_cloudwatch("CPUUsage", cpu_usage)
        publish_metric_to_cloudwatch("MemoryUsage", memory_usage)
        publish_metric_to_cloudwatch("DiskUsage", disk_usage)
        if network_latency is not None:
            publish_metric_to_cloudwatch("NetworkLatency", network_latency, unit="Milliseconds")

        time.sleep(CHECK_INTERVAL)
        

if __name__ == "__main__":
    main()
