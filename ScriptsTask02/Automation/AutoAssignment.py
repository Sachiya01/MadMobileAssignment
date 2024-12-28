import requests
import base64

# Jira API credentials
JIRA_URL = "https://sachithliyanage01.atlassian.net"
API_TOKEN = "ATATT3xFfGF0v2CHw_Bv3wUmZ17lCGRsceCl7Y2cqdiGd2u6SAcgZis4pgRqMfa_AQRPTSjxkZMbsmGUK7XcyHgihKrifF2RQybDU224JHkPGYXlAJXtTBnNFD6jTPnzwEJeZOoTgLBg_9y3K0MO_8OJqTXzP6KEMfrOjTYzu1dsszYm4YjSkjw=AD89BFAD"
EMAIL = "sachithliyanage07@gmail.com"

# Encode email and API token for Basic Authentication
auth_string = f"{EMAIL}:{API_TOKEN}"
auth_header = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

# Define assignment criteria
TEAM_ASSIGNMENT = {
    "Database": "712020:1aca61d7-a561-4c1b-a40e-91e8ea64d957",  # Damian Database Team
    "Application": "712020:c3f0da9f-d762-4610-b744-a69245bbf24b", #Adithya Application Team
    "Site": "712020:2af6b031-1380-401b-b16f-b9239adfed71",  # Sachith Site Team
    "Network": "712020:2af6b031-1380-401b-b16f-b9239adfed71"  # Sachith Network Team
}

# Function to assign an issue
def assign_issue(issue_key, account_id):
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/assignee"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }
    payload = {"accountId": account_id}
    
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 204:
        print(f"Successfully assigned {issue_key} to {account_id}")
    else:
        print(f"Failed to assign {issue_key}. Error: {response.json()}")

# Function to fetch unassigned issues
def fetch_issues():
    url = f"{JIRA_URL}/rest/api/3/search"
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }
    query = {
        "jql": "assignee is EMPTY AND status = 'Open'",  # Adjust JQL as needed
        "fields": ["issuetype"]
    }
    
    response = requests.get(url, headers=headers, params=query)
    if response.status_code == 200:
        issues = response.json().get("issues", [])
        return issues
    else:
        print(f"Failed to fetch issues. Error: {response.json()}")
        return []

# Main function to process and assign issues
def auto_assign_issues():
    issues = fetch_issues()
    for issue in issues:
        issue_key = issue["key"]
        issue_type = issue["fields"]["issuetype"]["name"]
        
        account_id = TEAM_ASSIGNMENT.get(issue_type)
        if account_id:
            assign_issue(issue_key, account_id)
        else:
            print(f"No assignment rule for {issue_key} (type: {issue_type})")

# Run the auto-assignment process
if __name__ == "__main__":
    auto_assign_issues()
