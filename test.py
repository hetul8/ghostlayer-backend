import requests
import json

def test():
    url = "http://localhost:8000/mask"
    payload = {"text": "My email is test@example.com"}
    try:
        response = requests.post(url, json=payload)
        print("Status Code:", response.status_code)
        print("JSON Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
