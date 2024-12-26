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

# All configurations
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
    "disk": 60,  
    "network_latency": 100  
}

# I created a stop file for emergency stop cases
STOP_FILE = "stop.flag"

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')

def send_email_alert(subject, message):
    
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = ALERT_RECIPIENT
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "I'm adding an example body"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Email alert sent to {ALERT_RECIPIENT}")
    except Exception as e:
        print(f"Error sending email: {e}")


def log_metrics():    

    data = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "timestamp": time.time()
        }
        
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
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    disk_usage = psutil.disk_usage('/').percent
    network_latency = measure_latency(PING_HOST)
    return cpu_usage, memory_usage, disk_usage, network_latency

def measure_latency(host):
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

def main():
    print("Monitoring started. To stop monitoring, create a file named 'stop.flag'.")

    while True:
        # Check if stop file exists
        if os.path.exists(STOP_FILE):
            print("Stop file detected. Terminating monitoring.")
            break
        log_metrics()
        cpu_usage, memory_usage, disk_usage, network_latency = monitor_system()
        print(f"CPU: {cpu_usage}%, Memory: {memory_usage}%, Disk: {disk_usage}%, Latency: {network_latency} ms")

        # Publishing metrics to CloudWatch
        publish_metric_to_cloudwatch("CPUUsage", cpu_usage)
        publish_metric_to_cloudwatch("MemoryUsage", memory_usage)
        publish_metric_to_cloudwatch("DiskUsage", disk_usage)
        if network_latency is not None:
            publish_metric_to_cloudwatch("NetworkLatency", network_latency, unit="Milliseconds")

        time.sleep(CHECK_INTERVAL)
        

if __name__ == "__main__":
    main()
    
