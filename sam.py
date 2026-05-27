import requests
import json

API_KEY = "PASTE_YOUR_NEW_API_KEY"

url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={API_KEY}"

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Say hello in Kannada"
                }
            ]
        }
    ]
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(
    url,
    headers=headers,
    data=json.dumps(payload)
)

print("Status Code:", response.status_code)
print(response.text)