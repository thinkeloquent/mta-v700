"""
Usage examples for fetch_auth_encoding.
"""
from fetch_auth_encoding import encode_auth

def example_basic_auth():
    print("--- Basic Auth ---")
    headers = encode_auth("basic", username="user1", password="password1")
    print(f"Headers: {headers}")
    # {'Authorization': 'Basic dXNlcjE6cGFzc3dvcmQx'}

def example_bearer_token():
    print("\n--- Bearer Token ---")
    headers = encode_auth("bearer", token="sk-123456")
    print(f"Headers: {headers}")
    # {'Authorization': 'Bearer sk-123456'}

def example_custom_header():
    print("\n--- Custom Header ---")
    headers = encode_auth("custom_header", header_key="X-My-Service", header_value="secret-val")
    print(f"Headers: {headers}")
    # {'X-My-Service': 'secret-val'}

if __name__ == "__main__":
    example_basic_auth()
    example_bearer_token()
    example_custom_header()
