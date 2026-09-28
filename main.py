import os
import requests
from dotenv import load_dotenv

# .env file se environment variables load karein
load_dotenv()

HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
BASE_URL = "https://api.hubapi.com/crm/v3/objects/contacts"

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# 1. Pagination: Saare Contacts Fetch Karna Cursor Ke Saath
def fetch_all_contacts():
    print("--- 1. Fetching All Contacts (With Pagination & Properties) ---")
    all_contacts = []
    after = None
    
    # Custom properties jo hume chahiye
    params = {
        "limit": 10,
        "properties": ["firstname", "lastname", "email", "phone", "company"]
    }

    try:
        while True:
            if after:
                params["after"] = after

            response = requests.get(BASE_URL, headers=HEADERS, params=params)
            
            # Error handling (Rate limits / HTTP errors)
            if response.status_code == 429:
                print("❌ Rate limit exceeded (429). Please wait a moment.")
                break
            elif response.status_code != 200:
                print(f"❌ Failed to fetch contacts: {response.status_code} - {response.text}")
                break

            data = response.json()
            results = data.get("results", [])
            all_contacts.extend(results)

            # Pagination check
            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")

            if not after:
                break

        print(f"✅ Total Contacts Retrieved: {len(all_contacts)}")
        for contact in all_contacts:
            props = contact.get("properties", {})
            print(f"- ID: {contact.get('id')} | Name: {props.get('firstname')} {props.get('lastname')} | Email: {props.get('email')}")
        
        return all_contacts

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return []

# 2. POST Request: Naya Contact Create Karna
def create_contact(email, firstname, lastname):
    print("\n--- 2. Creating New Contact ---")
    payload = {
        "properties": {
            "email": email,
            "firstname": firstname,
            "lastname": lastname
        }
    }
    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=payload)
        if response.status_code == 201:
            contact = response.json()
            print(f"✅ Contact Created Successfully! ID: {contact.get('id')}")
            return contact.get("id")
        elif response.status_code == 409:
            print("⚠️ Contact with this email already exists.")
        else:
            print(f"❌ Failed to create contact: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error occurred: {e}")
    return None

# 3. PATCH Request: Existing Contact Update Karna
def update_contact(contact_id, phone_number):
    print(f"\n--- 3. Updating Contact (ID: {contact_id}) ---")
    url = f"{BASE_URL}/{contact_id}"
    payload = {
        "properties": {
            "phone": phone_number
        }
    }
    try:
        response = requests.patch(url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            print("✅ Contact Updated Successfully!")
        else:
            print(f"❌ Failed to update contact: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    # Test 1: Saare contacts fetch karna
    contacts = fetch_all_contacts()
    
    # Test 2: Dummy Contact Create Karna (Aap email change kar sakte hain)
    new_id = create_contact("test.user2@example.com", "Test", "User")
    
    # Test 3: Agar contact create hua toh use update karna
    if new_id:
        update_contact(new_id, "9876543210")