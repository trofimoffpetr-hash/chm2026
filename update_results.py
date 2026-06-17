# -*- coding: utf-8 -*-
"""
Обновляет results.json результатами группового этапа ЧМ-2026
с football-data.org. Запускается роботом GitHub Actions по расписанию.
API-ключ берётся из переменной окружения FOOTBALL_DATA_TOKEN (секрет репозитория).
"""
import json, os, sys, datetime, urllib.request, urllib.error

COMP = "WC"
TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()

# FIFA three-letter code -> русское имя (как в ставках)
TLA = {
    "FRA": "Франция", "ENG": "Англия", "ESP": "Испания", "POR": "Португалия",
    "ARG": "Аргентина", "BRA": "Бразилия", "NED": "Нидерланды", "BEL": "Бельгия",
    "GER": "Германия", "NOR": "Норвегия", "MAR": "Марокко", "JPN": "Япония",
    "SUI": "Швейцария", "URU": "Уругвай", "CIV": "Кот-д'Ивуар", "GHA": "Гана",
    "BIH": "Босния и Герцеговина", "TUR": "Турция", "AUT": "Австрия", "ALG": "Алжир",
    "IRN": "Иран", "ECU": "Эквадор", "SCO": "Шотландия", "CAN": "Канада", "UZB": "Узбекистан",
}
NAME = {
    "france": "Франция", "england": "Англия", "spain": "Испания", "portugal": "Португалия",
    "argentina": "Аргентина", "brazil": "Бразилия", "netherlands": "Нидерланды", "belgium": "Бельгия",
    "germany": "Германия", "norway": "Норвегия", "morocco": "Марокко", "japan": "Япония",
    "switzerland": "Швейцария", "uruguay": "Уругвай", "côte d'ivoire": "Кот-д'Ивуар",
    "cote d'ivoire": "Кот-д'Ивуар", "ivory coast": "Кот-д'Ивуар", "ghana": "Гана",
    "bosnia and herzegovina": "Босния и Герцеговина", "bosnia-herzegovina": "Босния и Герцеговина",
    "turkey": "Турция", "türkiye": "Турция", "turkiye": "Турция", "austria": "Австрия",
    "algeria": "Алжир", "iran": "Иран", "ir iran": "Иран", "ecuador": "Эквадор",
    "scotland": "Шотландия", "canada": "Канада", "uzbekistan": "Узбекистан",
}

def ru_name(team):
    tla = (team.get("tla") or "").upper()
    if tla in TLA:
        return TLA[tla]
    return NAME.get((team.get("name") or "").strip().lower())

def fetch_matches():
    url = "https://api.football-data.org/v4/competitions/%s/matches" % COMP
    req = urllib.request.Request(url, headers={"X-Auth-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def compute():
    data = fetch_matches()
    per = {}
    done = 0
    for m in data.get("matches", []):
        if m.get("stage", "") not in ("GROUP_STAGE", "GROUP"):
            continue
        if m.get("status") != "FINISHED":
            continue
        done += 1
        winner = (m.get("score") or {}).get("winner")
        date = m.get("utcDate", "")
        for team, side in ((m.get("homeTeam", {}), "HOME"), (m.get("awayTeam", {}), "AWAY")):
            name = ru_name(team)
            if not name:
                continue
            if winner == "DRAW":
                res = "D"
            elif winner == "%s_TEAM" % side:
                res = "W"
            elif winner in ("HOME_TEAM", "AWAY_TEAM"):
                res = "L"
            else:
                continue
            per.setdefault(name, []).append((date, res))
    teams = {}
    for name, lst in per.items():
        lst.sort(key=lambda x: x[0])
        slots = ["", "", ""]
        for i, (_, r) in enumerate(lst[:3]):
            slots[i] = r
        teams[name] = slots
    msk = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    return {"teams": teams, "updatedAt": msk.strftime("%H:%M:%S"),
            "date": msk.strftime("%Y-%m-%d"), "matches": done}

def main():
    if not TOKEN:
        print("Нет FOOTBALL_DATA_TOKEN", file=sys.stderr)
        sys.exit(1)
    payload = compute()
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("OK: %d сыгранных матчей, %d команд" % (payload["matches"], len(payload["teams"])))

if __name__ == "__main__":
    main()
