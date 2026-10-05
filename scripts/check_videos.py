"""Проверка роликов YouTube: ссылка открывается, есть название, канал и длительность.

Содержимое ролика так не проверить — его должен посмотреть человек. Скрипт отвечает только
на вопрос «ссылка живая и сколько минут идёт».
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "ru,en;q=0.8"}


def get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def check(video_id):
    watch = f"https://www.youtube.com/watch?v={video_id}"
    try:
        meta = json.loads(get("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch, "")))
    except urllib.error.HTTPError as error:
        return {"id": video_id, "ok": False, "why": f"oembed {error.code} — ролик удалён или закрыт"}
    except Exception as error:  # сеть
        return {"id": video_id, "ok": False, "why": f"нет ответа: {error}"}

    seconds, why = None, ""
    try:
        page = get(watch)
        found = re.search(r'"lengthSeconds":"(\d+)"', page)
        if found:
            seconds = int(found.group(1))
        if '"isFamilySafe":false' in page:
            why = "помечен как не для детей"
    except Exception as error:
        why = f"длительность не прочиталась: {error}"

    return {
        "id": video_id,
        "ok": True,
        "title": meta.get("title", ""),
        "channel": meta.get("author_name", ""),
        "seconds": seconds,
        "why": why,
    }


for vid in sys.argv[1:]:
    row = check(vid)
    if not row["ok"]:
        print(f"[нет] {row['id']}: {row['why']}")
        continue
    length = f"{row['seconds'] // 60}:{row['seconds'] % 60:02d}" if row["seconds"] else "?"
    mark = "ok " if row["seconds"] and 60 <= row["seconds"] <= 420 else "длина"
    print(f"[{mark}] {row['id']} {length:>6}  {row['channel']} — {row['title']} {row['why']}")
