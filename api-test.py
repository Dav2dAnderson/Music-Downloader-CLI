import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.deezer.com/search",
            params={'q': 'Lil Wayne', "limit": 5}
        ) as resp: 
            data = await resp.json()
    
    for track in data.get("data", []):
        print(f"{track['artist']['name']} - {track['title']}")
        print(f"Preview: {track['preview']}")
        print(f"Duration: {track['duration']}s")

asyncio.run(main())