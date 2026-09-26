import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")

def test_hubspot_connection():
    if not HUBSPOT_ACCESS_TOKEN:
        print("Error: HUBSPOT_ACCESS_TOKEN is not set in .env file!")
        return

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("✅ HubSpot API Connection Successful!")
        data = response.json()
        print(f"Total Contacts Fetched: {len(data.get('results', []))}")
    else:
        print(f"❌ Failed to connect: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_hubspot_connection()