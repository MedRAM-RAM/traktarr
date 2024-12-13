import requests
import time
from config import settings

# Configuration
TRAKT_CLIENT_ID = settings['TRAKT_CLIENT_ID']
TRAKT_CLIENT_SECRET = settings['TRAKT_CLIENT_SECRET']
BASE_URL = "https://api.trakt.tv"

# Step 1: Request Device Code and User Code
def get_device_code():
    url = f"{BASE_URL}/oauth/device/code"
    headers = {"Content-Type": "application/json", "trakt-api-key": TRAKT_CLIENT_ID}
    payload = {"client_id": TRAKT_CLIENT_ID}

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Step 2: Poll for Access Token
def poll_for_access_token(device_code):
    url = f"{BASE_URL}/oauth/device/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "code": device_code,
        "client_id": TRAKT_CLIENT_ID,
        "client_secret": TRAKT_CLIENT_SECRET,
    }

    while True:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data  # Access token, refresh token, and expiry
        elif response.status_code == 400:
            print("Authorization pending. Please approve in your browser...")
        elif response.status_code == 404:
            print("Invalid device code. Exiting.")
            break
        elif response.status_code == 429:
            print("Polling too frequently. Waiting...")
            time.sleep(1)
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break

        time.sleep(5)  # Poll interval recommended by Trakt API

    return None

if __name__ == "__main__":
    # Step 1: Get Device Code and User Code
    print("Requesting device code...")
    device_code_data = get_device_code()

    if not device_code_data:
        print("Failed to retrieve device code. Exiting.")
        exit(1)

    device_code = device_code_data["device_code"]
    user_code = device_code_data["user_code"]
    verification_url = device_code_data["verification_url"]

    print("\nFollow these steps to authorize the app:")
    print(f"1. Go to: {verification_url}")
    print(f"2. Enter the User Code: {user_code}")
    print(f"3. Once approved, this script will automatically continue.\n")

    # Step 2: Poll for Access Token
    print("Polling for access token...")
    access_token_data = poll_for_access_token(device_code)

    if access_token_data:
        print("\nAuthorization successful!")
        print("\nIMPORTANT: Update your settings.local.yaml with the following value:")
        print(f'\nTRAKT_ACCESS_TOKEN: "{access_token_data["access_token"]}"')
    else:
        print("\nFailed to retrieve access token. Exiting.")
