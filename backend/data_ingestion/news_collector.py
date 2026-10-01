from datetime import datetime, timezone
from xml.etree import ElementTree

import httpx


async def fetch_rss(url: str, keywords: tuple[str, ...] = ()) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    root = ElementTree.fromstring(response.content)
    entries = []
    for item in root.findall(".//item"):
        title = item.findtext("title", default="").strip()
        description = item.findtext("description", default="").strip()
        if keywords and not any(word.casefold() in f"{title} {description}".casefold() for word in keywords):
            continue
        entries.append(
            {
                "source": root.findtext("./channel/title", default="RSS"),
                "title": title,
                "content": description,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return entries