import asyncio
import aiohttp

from yt_dlp import YoutubeDL

from model import AudioTrack

class MusicDownload:
    async def _search(self, query: str, limit: int = 3, ):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.deezer.com/search",
                params = {
                    "q": query, 
                    "limit": limit,
                    }
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        
        tracks = []
        
        for track in data.get('data', []):
            tracks.append(
                AudioTrack(
                    name=track['title'],
                    author=track['artist']['name'],
                    preview_url=track['preview'],
                    duration=track['duration'],
                )
            )
        return tracks


    async def search_by_name(self, name: str):
        return await self._search(name)

    
    async def search_by_author(self, author: str):
        return await self._search(author)
    
    async def search_by_popularity(self, limit: int = 10):

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.deezer.com/chart/0/tracks"
            ) as resp:

                resp.raise_for_status()
                data = await resp.json()

        tracks = []

        for track in data.get("data", [])[:limit]:

            tracks.append(
                AudioTrack(
                    name=track["title"],
                    author=track["artist"]["name"],
                    preview_url=track["preview"],
                    duration=track["duration"],
                )
            )

        return tracks
    

    # By genre
    async def get_genre_id(self, genre_name: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.deezer.com/genre"
            ) as resp:
                data = await resp.json()
        
        for genre in data.get("data", []):
            if genre['name'].lower() == genre_name.lower():
                return genre['id']
        return None

    async def search_by_genre(self, genre: str):
        genre_id = await self.get_genre_id(genre)

        if genre_id is None:
            return []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.deezer.com/genre/{genre_id}/artists"
            ) as resp:
                data = await resp.json()
        
        return data


async def download_audio(query: str) -> str:
    def _download():
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "music/%(title)s.%(ext)s",
            "quiet": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch1:{query}",
                download=True,
            )
            entry = info['entries'][0]
            return ydl.prepare_filename(entry)
    return await asyncio.to_thread(_download)
    

async def main():
    music = MusicDownload()

    while True:
        print("\n=== Music Search ===")
        print("1. Search by name")
        print("2. Search by author")
        print("3. Popular tracks")
        print("0. Exit")

        choice = input("Choose option: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            query = input("Song name: ")

            tracks = await music.search_by_name(query)

        elif choice == "2":
            query = input("Artist name: ")

            tracks = await music.search_by_author(query)

        elif choice == "3":
            tracks = await music.search_by_popularity()

        else:
            print("Invalid option")
            continue

        if not tracks:
            print("Nothing found")
            continue

        print("\nResults:")

        for i, track in enumerate(tracks, start=1):
            print(
                f"{i}. "
                f"{track.author} - {track.name} "
                f"({track.duration}s)"
            )

        selected = input(
            "\nChoose track number to download "
            "(Enter to skip): "
        ).strip()

        if not selected:
            continue

        try:
            track = tracks[int(selected) - 1]
        except (ValueError, IndexError):
            print("Invalid selection")
            continue

        print("Downloading...")

        path = await download_audio(
            f"{track.author} - {track.name}"
        )

        track.url = path

        print(f"Saved: {track.url}")


if __name__ == "__main__":
    asyncio.run(main())