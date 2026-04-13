import requests
import os

WEBHOOK = os.environ["WEBHOOK"]

r = requests.post(
    WEBHOOK,
    json={"content": "test message from github bot"},
    timeout=15
)

print(r.status_code)
print(r.text)
