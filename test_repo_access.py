import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

import httpx
from github_client import get_installation_token, _headers

INSTALLATION_ID = 176959847
REPO = "Monesh391/pr-reviewer"


async def main():
    token = await get_installation_token(INSTALLATION_ID)

    print("Installation token generated successfully!")

    url = f"https://api.github.com/repos/{REPO}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            headers=_headers(token)
        )

    print("Repository status:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        print("Repository:", data["full_name"])
        print("Private:", data["private"])
        print("Access:", "Successful")
    else:
        print("Error:", response.text)


if __name__ == "__main__":
    asyncio.run(main())