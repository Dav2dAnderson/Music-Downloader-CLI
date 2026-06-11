import asyncio
import aiohttp

from yt_dlp import YoutubeDL

from model import AudioTrack, SearchResult


class MusicDownload:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            print("Opened")
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_json(self, url: str, params: dict | None = None) -> dict:
        session = await self._get_session()
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _build_track(self, track: dict) -> AudioTrack:
        return AudioTrack(
            name=track["title"],
            author=track["artist"]["name"],
            preview_url=track["preview"],
            duration=track.get("duration"),
        )

    # общий поиск через Deezer (чтобы не дублировать код)
    async def _search(self, query: str, limit: int = 5, page: int = 1) -> SearchResult:
        index = (page - 1) * limit
        data = await self._get_json(
            "https://api.deezer.com/search",
            params={
                "q": query,
                "limit": limit,
                "index": index,
            }
        )

        tracks = [self._build_track(track) for track in data.get("data", [])]

        return SearchResult(
            tracks=tracks,
            total=data.get("total", 0),
            page=page,
            limit=limit,
            has_next=data.get("next") is not None,
        )

    # поиск по названию трека
    async def search_by_name(self, name: str, limit: int = 5, page: int = 1):
        return await self._search(name, limit, page)

    # поиск по артисту
    async def search_by_author(self, author: str, limit: int = 5, page: int = 1):
        return await self._search(author, limit, page)

    # популярные треки (чарт Deezer)
    async def search_by_popularity(self, limit: int = 5, page: int = 1):
        index = (page - 1) * limit
        data = await self._get_json(
            "https://api.deezer.com/chart/0/tracks",
            params={"limit": limit, "index": index},
        )

        tracks = [self._build_track(track) for track in data.get("data", [])[:limit]]

        return SearchResult(
            tracks=tracks,
            total=data.get("total", 0),
            page=page,
            limit=limit,
            has_next=data.get("next") is not None,
        )

    # получаем id жанра по имени
    async def get_genre_id(self, genre_name: str):
        data = await self._get_json("https://api.deezer.com/genre")

        for genre in data.get("data", []):
            if genre["name"].lower() == genre_name.lower():
                return genre["id"]

        return None  # если жанр не найден

    # поиск по жанру (через genre id)
    async def search_by_genre(self, genre: str, limit: int = 5, page: int = 1):
        genre_id = await self.get_genre_id(genre)

        if genre_id is None:
            return SearchResult(tracks=[], total=0, page=page, limit=limit, has_next=False)

        data = await self._get_json(
            f"https://api.deezer.com/genre/{genre_id}/artists",
            params={
                "limit": limit,
                "index": (page - 1) * limit,
            },
        )

        return SearchResult(
            tracks=[],
            total=data.get("total", 0),
            page=page,
            limit=limit,
            has_next=data.get("next") is not None,
        )


# скачивание аудио через yt_dlp (вынесено отдельно от класса)
async def download_audio(query: str) -> str:

    def _download():

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "music/%(title)s.%(ext)s",
            "quiet": True,
        }

        with YoutubeDL(ydl_opts) as ydl:

            # ищем видео через yt search и сразу скачиваем
            info = ydl.extract_info(
                f"ytsearch1:{query}",
                download=True,
            )

            entry = info['entries'][0]

            # получаем путь к файлу
            return ydl.prepare_filename(entry)

    # запускаем blocking код в отдельном потоке
    return await asyncio.to_thread(_download)



# CLI приложение (интерактивное меню)
async def main():

    music = MusicDownload()

    async def paginate_search(fetch_fn):
        page = 1
        while True:
            result = await fetch_fn(page)
            print(f"\nResults: {len(result.tracks)} | Total: {result.total} | Page: {result.page}")

            for i, track in enumerate(result.tracks, start=1):
                print(f"{i}. {track.author} - {track.name} ({track.duration}s)")

            print("\n[n] Next [p] Previous [0] Exit or options")
            action = input(">>").strip()

            if action == 'n' and result.has_next:
                page += 1
                continue
            elif action == "p" and page > 1:
                page -= 1
                continue
            elif action == "0":
                return []
            elif action.isdigit():
                return result.tracks

    try:
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
                tracks = await paginate_search(
                    lambda page: music.search_by_name(name=query, page=page)
                )

            elif choice == "2":
                query = input("Artist name: ")
                tracks = await paginate_search(
                    lambda page: music.search_by_author(author=query, page=page)
                )

            elif choice == "3":
                tracks = await paginate_search(
                    lambda page: music.search_by_popularity(page=page)
                )

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
                "\nChoose track number to download (Enter to skip): "
            ).strip()

            if not selected:
                continue

            try:
                track = tracks[int(selected) - 1]
            except (ValueError, IndexError):
                print("Invalid selection")
                continue

            print("Downloading...")

            # скачиваем полный трек через yt_dlp
            path = await download_audio(
                f"{track.author} - {track.name}"
            )

            # сохраняем локальный путь в модель
            track.url = path

            print(f"Saved: {track.url}")
            
    finally:
        await music.close()
        print("Closed")

# точка входа
if __name__ == "__main__":
    asyncio.run(main())