import requests
import base64
from datetime import datetime

# Jira API credentials
JIRA_URL = "https://sachithliyanage01.atlassian.net"
API_TOKEN = "ATATT3xFfGF06MsEOkk1fMKsq5iDUaSFuWilsl0ibHZvEo1JxkvybrzVYRSQRXoqbUMUbXaY5gq9i9MI70qSEz25lqfPiPgV-Um-g7Wflujj0FhXmgS9cFtZQpzxwXHSyzPvExajT901BrjHDGONda6L2OwC3Kba-yfR5cSYUIyb1Bnzb_shlGg=0154E176"
EMAIL = "sachithliyanage07@gmail.com"

auth_string = f"{EMAIL}:{API_TOKEN}"
auth_header = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

# Severity thresholds for updating and escalation 
SEVERITY_UPDATE_RULES = {
    "Low": 15,  # 0–15 seconds
    "Medium": 45,      # 15–45 seconds
    "High": 80,    # 45–80 seconds
    "Highest": 120       # >80 seconds
}

ESCALATION_RULES = {
     "Low": 15,  # 0–15 seconds
    "Medium": 45,      # 15–45 seconds
    "High": 80,    # 45–80 seconds
    "Highest": 120 
}

# Function to fetch incidents
def fetch_incidents():
    url = f"{JIRA_URL}/rest/api/3/search"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }
    query = {
        "jql": "issuetype = 'Offsite Tower' AND status = 'Open'",  # Only Offsite issues are configured to escalate since testing would be hard if all issues escalated.
        "fields": ["key", "created", "customfield_10057"]   #Custom field ID should be added here
    }
    
    response = requests.get(url, headers=headers, params=query)
    if response.status_code == 200:
        return response.json().get("issues", [])
    else:
        print(f"Failed to fetch incidents. Error: {response.json()}")
        return []

# Function to calculate time elapsed
def time_elapsed(created_time):
    created_dt = datetime.strptime(created_time, "%Y-%m-%dT%H:%M:%S.%f%z")
    now_dt = datetime.now(created_dt.tzinfo)
    elapsed = now_dt - created_dt
    return elapsed.total_seconds()  

# Function to update the severity field of an issue
def update_severity(issue_key, new_severity):
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": {
            "customfield_10057": {"value": new_severity}  #Custom field ID should be added here
        }
    }
    
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 204:
        print(f"Successfully updated severity of {issue_key} to {new_severity}")
    else:
        print(f"Failed to update severity of {issue_key}. Error: {response.json()}")

# Function to determine new severity based on time elapsed
def determine_severity(elapsed_time):
    for severity, threshold in SEVERITY_UPDATE_RULES.items():
        if elapsed_time <= threshold:
            return severity
    return "Highest"  # Default to Low if no match

# Function to escalate incident
def escalate_incident(issue_key):
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }
    payload = {
        "transition": {"id": "711"}  # Replace with the transition ID for "Escalated"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 204:
        print(f"Successfully escalated {issue_key}")
    else:
        print(f"Failed to escalate {issue_key}. Error: {response.json()}")
# Main function to process and update severity
def auto_update_and_escalate():
    incidents = fetch_incidents()
    for incident in incidents:
        issue_key = incident["key"]
        created_time = incident["fields"]["created"]
        
        # Calculate elapsed time
        elapsed_time = time_elapsed(created_time)
        
        # Determine new severity
        new_severity = determine_severity(elapsed_time)
        
        # Extract current severity
        severity_field = incident["fields"].get("customfield_10057", {})  #Custom field ID should be added here
        current_severity = severity_field.get("value", "Unknown") if isinstance(severity_field, dict) else severity_field
        
        # Update severity if it has changed
        if new_severity != current_severity:
            print(f"Updating severity for {issue_key} from {current_severity} to {new_severity}")
            update_severity(issue_key, new_severity)
        else:
            print(f"Severity for {issue_key} is already {current_severity}, no update needed.")
        
        # Handle escalation explicitly for "Highest" severity
        if new_severity == "Highest":
            print(f"Issue {issue_key} has reached the 'Highest' severity. Attempting escalation.")
            escalate_incident(issue_key)
        else:
            # Escalate based on updated severity
            escalation_threshold = ESCALATION_RULES.get(new_severity, 150)
            if elapsed_time > escalation_threshold:
                print(f"Escalating issue {issue_key} with severity {new_severity}")
                escalate_incident(issue_key)
            else:
                print(f"Issue {issue_key} (Severity: {new_severity}) does not meet escalation criteria.")

if __name__ == "__main__":
    auto_update_and_escalate()
