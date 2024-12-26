import boto3
from datetime import datetime, timedelta, timezone
import time

# Initialize Boto3 clients which are the AWS SDK for python
cloudwatch = boto3.client('cloudwatch')
autoscaling = boto3.client('autoscaling')

# Function to get average CPU utilization
def get_cpu_utilization(instance_id):
    StartTime = datetime.now(timezone.utc) - timedelta(minutes=1)
    EndTime = datetime.now(timezone.utc)

    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[
            {'Name': 'InstanceId', 'Value': instance_id}
        ],
        StartTime=StartTime,
        EndTime=EndTime,
        Period=300,
        Statistics=['Average']
    )
    
    data_points = response.get('Datapoints', [])
    if not data_points:
        print(f"No data points for instance {instance_id} in the last miniute.")
        return None
    
    return data_points[0]['Average']

# Adjusts ASG capacity based on predetermined metrics
def scale_autoscaling_group(asg_name, desired_capacity):
    response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    asg = response['AutoScalingGroups'][0]

    min_size = asg['MinSize']
    max_size = asg['MaxSize']

    if desired_capacity < min_size or desired_capacity > max_size:
        print(f"Desired capacity {desired_capacity} is out of bounds ({min_size}-{max_size}).")
        return

    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=desired_capacity
    )
    print(f"Scaling action performed: New desired capacity = {desired_capacity}")

# Scales insatnces based on CPU utilization
def monitor_and_scale(asg_name, instance_ids, cpu_threshold, scale_out_increment=1, scale_in_decrement=1):
    while True:
        try:
            average_cpu = 0
            instance_count = len(instance_ids)
            
            for instance_id in instance_ids:
                cpu = get_cpu_utilization(instance_id)
                if cpu is not None:
                    average_cpu += cpu
            
            average_cpu /= instance_count

            print(f"Average CPU Utilization: {average_cpu}%")
            
            asg_response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
            asg = asg_response['AutoScalingGroups'][0]
            current_capacity = asg['DesiredCapacity']
            min_size = asg['MinSize']
            max_size = asg['MaxSize']

            print(f"Current Desired Capacity: {current_capacity}, MinSize: {min_size}, MaxSize: {max_size}")

            # Scale out (Increase capacity)
            if average_cpu > cpu_threshold and current_capacity + scale_out_increment <= max_size:
                print(f"Scaling out: Increasing capacity by {scale_out_increment}.")
                scale_autoscaling_group(asg_name, current_capacity + scale_out_increment)

            # Scale in (Decrease capacity)
            elif average_cpu < cpu_threshold and current_capacity - scale_in_decrement >= min_size:
                print(f"Scaling in: Decreasing capacity by {scale_in_decrement}.")
                scale_autoscaling_group(asg_name, current_capacity - scale_in_decrement)
            else:
                print("No scaling action required.")

        except Exception as e:
            print(f"An error occurred: {e}")

       
        time.sleep(10)

if __name__ == "__main__":
    AUTO_SCALING_GROUP_NAME = "Group1"
    INSTANCE_IDS = ["i-0df7fe96cdde60771"]  # Only one instance, CHANGEs WHENEVER THE STRESS TEST IS OVER SINCE INSTANCE SOMETIMES GETS TERMINATED. Therefore the instance has to be replaced every time this exact instance is terminated
    CPU_THRESHOLD = 60  # CPU threshold in percentage

    monitor_and_scale(AUTO_SCALING_GROUP_NAME, INSTANCE_IDS, CPU_THRESHOLD)
