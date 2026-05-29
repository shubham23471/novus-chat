import requests
import json

# Fetch OpenAPI spec
response = requests.get("http://localhost:8000/openapi.json")
spec = response.json()


# Create simple markdown
with open("/Users/shubham/saas/novus-chat/data/api_overview.md", "w") as f:
    f.write(f"# {spec['info']['title']}\n\n")
    f.write(f"**Base URL:** http://localhost:8000\n\n")
    
    f.write("## Endpoints\n\n")
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            summary = details.get('summary', '')
            f.write(f"### {method.upper()} {path}\n")
            f.write(f"**Summary:** {summary}\n\n")