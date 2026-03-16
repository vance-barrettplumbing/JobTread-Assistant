"""Run this to find the correct JobTread API endpoint."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("JOBTREAD_API_KEY")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}
test_query = '{"query":"{ __typename }"}'

candidates = [
    "https://api.jobtread.com/papi",
    "https://api.jobtread.com/graphql",
    "https://api.jobtread.com/api/graphql",
    "https://api.jobtread.com/v1/graphql",
    "https://api.jobtread.com/",
]

print(f"Testing with API key: {api_key[:8]}...\n")
for url in candidates:
    try:
        r = requests.post(url, data=test_query, headers=headers, timeout=8)
        print(f"  {r.status_code}  {url}")
        if r.status_code == 200:
            print(f"       -> {r.text[:120]}")
    except Exception as e:
        print(f"  ERR  {url}  ({e})")
