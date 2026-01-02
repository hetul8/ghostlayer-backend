import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_flow():
    print("Testing PII Masking API...")
    
    # 1. Mask
    text = "My email is john.doe@example.com and my friend is Alice Smith."
    print(f"\n[1] MASKING: '{text}'")
    
    try:
        response = requests.post(f"{BASE_URL}/mask", json={"text": text})
        response.raise_for_status()
        masked_data = response.json()
        masked_text = masked_data["masked_text"]
        print(f" -> Result: '{masked_text}'")
        
        if "john.doe@example.com" in masked_text:
            print("FAILED: Email not masked!")
            sys.exit(1)
        if "Alice Smith" in masked_text:
            print("FAILED: Name not masked!")
            sys.exit(1)
            
    except Exception as e:
        print(f"FAILED to mask: {e}")
        sys.exit(1)

    # 2. Unmask
    print(f"\n[2] UNMASKING: '{masked_text}'")
    try:
        response = requests.post(f"{BASE_URL}/unmask", json={"masked_text": masked_text})
        response.raise_for_status()
        unmasked_data = response.json()
        original_text = unmasked_data["original_text"]
        print(f" -> Result: '{original_text}'")
        
        if original_text != text:
            print(f"FAILED: Text mismatch!\nExpected: {text}\nGot:      {original_text}")
            sys.exit(1)
        else:
            print("SUCCESS: Original text restored.")
            
    except Exception as e:
        print(f"FAILED to unmask: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Wait for server to be up logic could be here, but we will run this manually after server starts
    test_flow()
