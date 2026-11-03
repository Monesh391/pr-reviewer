import asyncio
from dotenv import load_dotenv

# Load .env before importing github_client
load_dotenv(override=True)

import httpx
from github_client import _app_jwt, _headers


async def main():
    url = "https://api.github.com/app/installations"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            headers=_headers(_app_jwt()),
        )

    print("Status:", response.status_code)

    if response.status_code == 200:
        for installation in response.json():
            print("Installation ID:", installation["id"])
            print("Account:", installation["account"]["login"])
    else:
        print("Error:", response.text)


if __name__ == "__main__":
    asyncio.run(main())