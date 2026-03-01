import requests, json, os

key = os.environ.get("XAI_API_KEY", "")
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# Test Responses API with x_search
payload = {
    "model": "grok-4-1-fast-reasoning",
    "tools": [{"type": "x_search"}],
    "input": [
        {"role": "user", "content": "What are people saying about Bitcoin on X right now? Keep it brief."}
    ],
    "max_output_tokens": 500,
}

print("Testing Responses API with x_search...")
r = requests.post("https://api.x.ai/v1/responses", headers=headers, json=payload, timeout=120)
print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(f"Error: {r.text[:1000]}")
else:
    result = r.json()
    print(json.dumps(result, indent=2)[:3000])
