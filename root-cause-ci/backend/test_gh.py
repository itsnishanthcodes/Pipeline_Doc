import asyncio
from app.integrations.github_client import GitHubClient
from app.core.config import get_settings

async def test():
    token = get_settings().github_token
    github = GitHubClient(token)
    try:
        content = "print(\"hello\")"
        res = await github.create_or_update_file("Pranesh-1905/Foodloop", "math_utils.py", "test msg", content, "main")
        print(res)
    except Exception as e:
        if hasattr(e, "response"):
            print("HTTP ERROR:", e.response.status_code, e.response.text)
        else:
            print("ERROR:", e)

asyncio.run(test())
