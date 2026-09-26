"""Собирает research/online-resources.json и research/online-resources.md
из research/tools/online_resources_data.py.

    python3 research/tools/build_online_resources.py            # без проверки ссылок
    python3 research/tools/build_online_resources.py --check    # проверить доступность

Проверка делает GET с таймаутом и пишет статус в JSON: ok / http-<код> / нет ответа.
Российские сайты часто недоступны из-за рубежа и наоборот, поэтому «нет ответа» —
повод проверить вручную или через web.archive.org, а не вычёркивать источник.
"""
import concurrent.futures as cf
import datetime as dt
import json
import pathlib
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from online_resources_data import R, SOURCE_ARTICLES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2] / "research"
BRANCHES = {
    "ФЁД": "Фёдоровы: Слуцк/Павловск, угон 1943, Дармштадт",
    "СПБ": "Петербург/Ленинград и губерния",
    "РЯЗ": "Рязанская губ. (Михайловский, Скопинский у.)",
    "ТУЛ": "Тульская губ. (Богородицкий у.)",
    "ПЕН": "Пензенская губ.",
    "НОВ": "Новгородская губ. (Крестецкий у.)",
    "АРХ": "Архангельская губ. (Пинежский у.)",
    "БЕЛ": "Минская губ. / Беларусь",
    "ЭСТ": "Эстония (Ревель)",
}


def check(url):
    if not url.startswith("http"):
        return "не проверялось"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return "ok" if r.status < 400 else f"http-{r.status}"
    except urllib.error.HTTPError as e:
        return f"http-{e.code}"
    except Exception:
        return "нет ответа"


def wayback(url):
    """Ближайший снимок в web.archive.org для недоступной ссылки."""
    if not url.startswith("http"):
        return ""
    api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        with urllib.request.urlopen(api, timeout=40) as r:
            snap = json.load(r).get("archived_snapshots", {}).get("closest")
            return snap["url"] if snap and snap.get("available") else ""
    except Exception:
        return ""


def main():
    items = [
        dict(section=s, name=n, url=u, covers=c, access=a, branches=b, note=note)
        for s, n, u, c, a, b, note in R
    ]
    if "--check" in sys.argv:
        with cf.ThreadPoolExecutor(6) as ex:
            for it, st in zip(items, ex.map(check, [i["url"] for i in items])):
                it["status"] = st
            # второй заход для не ответивших: часть сайтов отвечает не с первого раза
            retry = [i for i in items if i["status"] == "нет ответа"]
            for it, st in zip(retry, ex.map(check, [i["url"] for i in retry])):
                it["status"] = st
            bad = [i for i in items if i["status"] not in ("ok", "не проверялось")]
            for it, snap in zip(bad, ex.map(wayback, [i["url"] for i in bad])):
                if snap:
                    it["archive"] = snap
        checked = dt.date.today().isoformat()
    else:
        old = {}
        p = ROOT / "online-resources.json"
        if p.exists():
            prev = json.loads(p.read_text())
            old = {i["url"]: i for i in prev["resources"]}
            checked = prev.get("checked_at")
        for it in items:
            for k in ("status", "archive"):
                if old.get(it["url"], {}).get(k):
                    it[k] = old[it["url"]][k]

    (ROOT / "online-resources.json").write_text(json.dumps(
        {"source_articles": SOURCE_ARTICLES, "checked_at": checked,
         "branches": BRANCHES, "resources": items},
        ensure_ascii=False, indent=1) + "\n")

    md = ["# Реестр онлайн-источников для генеалогического поиска", "",
          "Основа — «Сводный реестр онлайн-источников для генеалогического поиска», части "
          + ", ".join(f"[{i+1}]({u})" for i, u in enumerate(SOURCE_ARTICLES))
          + " (Пикабу, 2021). Ссылки восстановлены из исходного HTML, устаревшие адреса "
          "заменены, в «Для нас» — чем источник полезен нашим ветвям.", "",
          "Данные: [online-resources.json](online-resources.json); правка — в "
          "`research/tools/online_resources_data.py`, пересборка — "
          "`python3 research/tools/build_online_resources.py --check`.", ""]
    if checked:
        md += [f"Доступность ссылок проверена {checked} с компьютера владелицы архива. "
               "«нет ответа» не значит, что ресурс закрыт: часть сайтов открывается только "
               "из России или только через VPN.", ""]
    md += ["## Ветви", ""] + [f"- **{k}** — {v}" for k, v in BRANCHES.items()] + [""]

    md += ["## Сначала — для текущих поисков", ""]
    for it in items:
        if any(b in it["branches"] for b in ("ФЁД",)) and it["note"]:
            md.append(f"- [{it['name']}]({it['url']}) — {it['note']}")
    md.append("")

    section = None
    for it in items:
        if it["section"] != section:
            section = it["section"]
            md += ["", f"## {section}", "",
                   "| Источник | Что есть | Доступ | Ветви | Для нас | Статус |",
                   "|---|---|---|---|---|---|"]
        name = f"[{it['name']}]({it['url']})" if it["url"] else it["name"]
        cells = [name, it["covers"], it["access"], ", ".join(it["branches"]),
                 it["note"], it.get("status", "")
                 + (f" · [архив]({it['archive']})" if it.get("archive") else "")]
        md.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    (ROOT / "online-resources.md").write_text("\n".join(md) + "\n")
    print(len(items), "resources")


if __name__ == "__main__":
    main()
