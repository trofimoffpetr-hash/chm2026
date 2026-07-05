# -*- coding: utf-8 -*-
"""
Обновляет results.json результатами группового этапа ЧМ-2026
с football-data.org. Запускается роботом GitHub Actions по расписанию.
API-ключ берётся из переменной окружения FOOTBALL_DATA_TOKEN (секрет репозитория).
"""
import json, os, sys, datetime, urllib.request, urllib.error

COMP = "WC"
TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()

# FIFA three-letter code -> русское имя (все 48 команд ЧМ-2026)
TLA = {
    "FRA": "Франция", "ESP": "Испания", "ARG": "Аргентина", "ENG": "Англия", "POR": "Португалия",
    "BRA": "Бразилия", "NED": "Нидерланды", "MAR": "Марокко", "BEL": "Бельгия", "GER": "Германия",
    "CRO": "Хорватия", "COL": "Колумбия", "SEN": "Сенегал", "MEX": "Мексика", "USA": "США",
    "URU": "Уругвай", "NOR": "Норвегия", "CAN": "Канада", "EGY": "Египет", "ALG": "Алжир",
    "AUS": "Австралия", "KOR": "Южная Корея", "AUT": "Австрия", "ECU": "Эквадор", "TUR": "Турция",
    "IRN": "Иран", "SUI": "Швейцария", "JPN": "Япония",
    "CIV": "Кот-д'Ивуар", "PAN": "Панама", "PAR": "Парагвай", "SWE": "Швеция", "SCO": "Шотландия",
    "CZE": "Чехия", "COD": "ДР Конго", "TUN": "Тунис",
    "BIH": "Босния и Герцеговина", "JOR": "Иордания", "KSA": "Саудовская Аравия", "RSA": "ЮАР",
    "IRQ": "Ирак", "QAT": "Катар", "UZB": "Узбекистан",
    "CPV": "Кабо-Верде", "GHA": "Гана", "CUW": "Кюрасао", "HAI": "Гаити", "NZL": "Новая Зеландия",
}
NAME = {
    "france": "Франция", "spain": "Испания", "argentina": "Аргентина", "england": "Англия",
    "portugal": "Португалия", "brazil": "Бразилия", "netherlands": "Нидерланды", "morocco": "Марокко",
    "belgium": "Бельгия", "germany": "Германия", "croatia": "Хорватия", "colombia": "Колумбия",
    "senegal": "Сенегал", "mexico": "Мексика", "united states": "США", "usa": "США",
    "uruguay": "Уругвай", "norway": "Норвегия", "canada": "Канада", "egypt": "Египет", "algeria": "Алжир",
    "australia": "Австралия", "korea republic": "Южная Корея", "south korea": "Южная Корея",
    "austria": "Австрия", "ecuador": "Эквадор", "turkey": "Турция", "türkiye": "Турция",
    "turkiye": "Турция", "iran": "Иран", "ir iran": "Иран", "switzerland": "Швейцария", "japan": "Япония",
    "côte d'ivoire": "Кот-д'Ивуар", "cote d'ivoire": "Кот-д'Ивуар", "ivory coast": "Кот-д'Ивуар",
    "panama": "Панама", "paraguay": "Парагвай", "sweden": "Швеция", "scotland": "Шотландия",
    "czechia": "Чехия", "czech republic": "Чехия", "congo dr": "ДР Конго", "dr congo": "ДР Конго",
    "democratic republic of congo": "ДР Конго", "tunisia": "Тунис",
    "bosnia and herzegovina": "Босния и Герцеговина", "bosnia-herzegovina": "Босния и Герцеговина",
    "jordan": "Иордания", "saudi arabia": "Саудовская Аравия", "south africa": "ЮАР", "iraq": "Ирак",
    "qatar": "Катар", "uzbekistan": "Узбекистан", "cape verde": "Кабо-Верде", "cabo verde": "Кабо-Верде",
    "ghana": "Гана", "curacao": "Кюрасао", "curaçao": "Кюрасао", "haiti": "Гаити", "new zealand": "Новая Зеландия",
}

# стадии плей-офф (как их называет football-data)
PLAYOFF_STAGES = ("LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL")

# короткие подписи стадий для «последнего матча»
STAGE_SHORT_PY = {
    "GROUP_STAGE": "группа", "GROUP": "группа",
    "LAST_32": "1/16", "LAST_16": "1/8", "QUARTER_FINALS": "1/4",
    "SEMI_FINALS": "1/2", "THIRD_PLACE": "за 3-е", "FINAL": "финал",
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
    per = {}          # группа: команда -> [(дата, W/D/L), ...]
    playoff = {}      # плей-офф: команда -> {стадия: очки}
    done = 0          # сыграно матчей группы
    pdone = 0         # сыграно матчей плей-офф (учитываемых стадий)
    knockout = set()  # команды, попавшие в сетку плей-офф (любой статус матча)
    last = None       # последний сыгранный матч (максимальный utcDate)
    for m in data.get("matches", []):
        stage = m.get("stage", "")
        ht, at = m.get("homeTeam", {}), m.get("awayTeam", {})
        # команды сетки плей-офф — по всем матчам нокаута, любой статус
        if stage in PLAYOFF_STAGES or stage == "THIRD_PLACE":
            for team in (ht, at):
                nm = ru_name(team)
                if nm:
                    knockout.add(nm)
        if m.get("status") != "FINISHED":
            continue
        # последний сыгранный матч (для плашки «Посл. матч»)
        d = m.get("utcDate", "")
        if last is None or d > last[0]:
            last = (d, m)
        score = m.get("score") or {}
        winner = score.get("winner")
        if stage in ("GROUP_STAGE", "GROUP"):
            done += 1
            date = m.get("utcDate", "")
            for team, side in ((ht, "HOME"), (at, "AWAY")):
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
        elif stage in PLAYOFF_STAGES or stage == "THIRD_PLACE":
            pdone += 1
            dur = score.get("duration", "REGULAR")  # REGULAR / EXTRA_TIME / PENALTY_SHOOTOUT
            for team, side in ((ht, "HOME"), (at, "AWAY")):
                name = ru_name(team)
                if not name:
                    continue
                if winner not in ("HOME_TEAM", "AWAY_TEAM"):
                    continue
                iswin = (winner == "%s_TEAM" % side)
                if dur == "REGULAR":
                    pts = 3 if iswin else 0
                else:
                    pts = 2 if iswin else 1  # ОТ или пенальти
                playoff.setdefault(name, {})[stage] = pts
    teams = {}
    for name, lst in per.items():
        lst.sort(key=lambda x: x[0])
        slots = ["", "", ""]
        for i, (_, r) in enumerate(lst[:3]):
            slots[i] = r
        teams[name] = slots
    # строка последнего сыгранного матча
    last_match, last_stage = "", ""
    if last is not None:
        _, lm = last
        lht, lat = lm.get("homeTeam", {}), lm.get("awayTeam", {})
        hn = ru_name(lht) or lht.get("shortName") or lht.get("name") or "?"
        an = ru_name(lat) or lat.get("shortName") or lat.get("name") or "?"
        ft = (lm.get("score") or {}).get("fullTime") or {}
        hs = ft.get("home")
        as_ = ft.get("away")
        hs = hs if hs is not None else "-"
        as_ = as_ if as_ is not None else "-"
        dur = (lm.get("score") or {}).get("duration", "REGULAR")
        suf = " пен." if dur == "PENALTY_SHOOTOUT" else (" ОТ" if dur == "EXTRA_TIME" else "")
        last_match = "%s %s:%s%s %s" % (hn, hs, as_, suf, an)
        last_stage = STAGE_SHORT_PY.get(lm.get("stage", ""), "")
    msk = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    return {"teams": teams, "playoff": playoff,
            "updatedAt": msk.strftime("%H:%M:%S"), "date": msk.strftime("%Y-%m-%d"),
            "matches": done, "playoffMatches": pdone,
            "lastMatch": last_match, "lastMatchStage": last_stage,
            "knockoutTeams": sorted(knockout)}

def main():
    if not TOKEN:
        print("Нет FOOTBALL_DATA_TOKEN", file=sys.stderr)
        sys.exit(1)
    payload = compute()
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("OK: группа %d матчей (%d команд), плей-офф %d матчей (%d команд)" % (
        payload["matches"], len(payload["teams"]),
        payload["playoffMatches"], len(payload["playoff"])))

if __name__ == "__main__":
    main()
