from calendar import isleap
from datetime import date, timedelta


MONTHS = "ian. febr. mart. apr. maii iun. iul. aug. sept. oct. nov. dec.".split()
# General Calendar celebrations that can take precedence over an ordinary Sunday.
FIXED_OCCURRENCES = {
    (2, 2), (6, 24), (6, 29), (8, 6), (8, 15),
    (9, 14), (11, 1), (11, 2), (11, 9),
}


def sunday_on_or_after(day):
    return day + timedelta(days=(6 - day.weekday()) % 7)


def roman(number):
    numeral = ""
    for value, letters in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        count, number = divmod(number, value)
        numeral += letters * count
    return numeral


def calendar(easter):
    year = easter.year
    baptism = sunday_on_or_after(date(year, 1, 7))
    second_christmas = sunday_on_or_after(date(year, 1, 2))
    christmas_sunday = sunday_on_or_after(date(year, 12, 26))
    ash = easter - timedelta(days=46)
    pentecost = easter + timedelta(days=49)
    trinity = pentecost + timedelta(days=7)
    advent = sunday_on_or_after(date(year, 11, 27))
    king = advent - timedelta(days=7)
    rows = {
        "Dominica II post Nativitatem": (
            second_christmas if second_christmas.day < 6 else None),
        "Baptisma Domini": baptism,
        "Feria IV Cinerum": ash,
        "Dominica in Palmis": easter - timedelta(days=7),
        "Dominica Resurrectionis": easter,
        "Ascensio Domini": easter + timedelta(days=39),
        "Dominica Pentecostes": pentecost,
        "Sanctissima Trinitas": trinity,
        "SS. Corpus et Sanguis Christi": easter + timedelta(days=60),
        "Sacratissimum Cor Iesu": easter + timedelta(days=68),
        "Christus Universorum Rex": king,
        "Sancta Familia": (christmas_sunday if christmas_sunday.year == year
                           else date(year, 12, 30)),
    }
    for week in range(1, 6):
        rows[f"Dominica {roman(week)} Quadragesimæ"] = easter - timedelta(weeks=7-week)
    for week in range(2, 8):
        rows[f"Dominica {roman(week)} Paschæ"] = easter + timedelta(weeks=week-1)
    for week in range(1, 5):
        rows[f"Dominica {roman(week)} Adventus"] = advent + timedelta(weeks=week-1)
    for week in range(2, 34):
        before = baptism + timedelta(weeks=week-1)
        after = king - timedelta(weeks=34-week)
        rows[f"Dominica {roman(week)} per annum"] = (
            before if before < ash else after if after > pentecost else None)
    return rows


def table(years, calendars, groups, abbreviate=False, matching_years=None):
    outer_rule = r"\BookCalendarOuterRule" if abbreviate else r"\hline"
    # Both pages use the same widths even when their celebration names differ.
    label_column = r"W{l}{.17\linewidth}" if abbreviate else "l"
    year_column = r"W{c}{3em}" if abbreviate else "c"
    columns = rf"{label_column}*{{{len(years)}}}{{{year_column}}}"
    header = r"""
\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}TABLE_COLUMNS@{}}
\arrayrulecolor{gregoriocolor}
OUTER_RULE
"""
    header = header.replace("TABLE_COLUMNS", columns).replace("OUTER_RULE", outer_rule)
    year_headers = [
        rf"\textbf{{{year}}}" + (r"\textsuperscript{b}" if isleap(year) else "")
        for year in years
    ]
    label_header = r"\textbf{Celebratio}"
    if abbreviate:
        label_header = r"\rule[-6pt]{0pt}{21pt}"
    header += " & ".join([label_header, *year_headers]) + r" \\" + "\n"
    if matching_years:
        # Match the year rows on both pages despite their different body leading.
        matching_label = r"\rule[-5.1pt]{0pt}{17pt}" if abbreviate else ""
        header += " & ".join([matching_label, *(rf"\textbf{{{matching_years.get(year, '')}}}"
                                                 for year in years)]) + r" \\" + "\n"
        header += r"\noalign{\vskip 2pt}" + "\n"
    header += "\\hline\n"
    rows = []
    for heading, labels in groups:
        rows.append(rf"\multicolumn{{{len(years) + 1}}}{{@{{}}l}}{{\textcolor{{gregoriocolor}}{{\textbf{{{heading}}}}}}} \\")
        for label in labels:
            cells = []
            for days in calendars:
                day = days[label]
                if day is None:
                    cells.append("—")
                    continue
                cell = day_month(day, abbreviate, align=abbreviate)
                if label.endswith("per annum") and (
                    day == days["Sanctissima Trinitas"]
                    or (day.month, day.day) in FIXED_OCCURRENCES
                ):
                    cell = rf"\textit{{{cell}}}"
                cells.append(cell)
            display_label = missale_label(label) if abbreviate else label
            rows.append(display_label + " & " + " & ".join(cells) + r" \\")
    row_end = "\n"
    adjustment = ""
    if abbreviate:
        row_end = "\n" + r"\noalign{\vskip\BookMissaleRowAdjustment}" + "\n"
        adjustment = r"\noalign{\vskip\BookMissaleTableRemainder}" + "\n"
    return header + row_end.join(rows) + row_end + adjustment + outer_rule + "\n\\end{tabular*}\n"


def second_reading_table():
    """Tabella II, with each new epistle printed on its first Sunday."""
    cycles = (
        {2: "1 ad Corinthios, 1--4", 9: "ad Romanos", 25: "ad Philippenses",
         29: "1 ad Thessalonicenses"},
        {2: "1 ad Corinthios, 6--11", 7: "2 ad Corinthios", 15: "ad Ephesios",
         22: "Iacobi", 27: "ad Hebræos, 2--10"},
        {2: "1 ad Corinthios, 12--15", 9: "ad Galatas", 15: "ad Colossenses",
         19: "ad Hebræos, 11--12", 23: "ad Philemonem", 24: "1 ad Timotheum",
         27: "2 ad Timotheum", 31: "2 ad Thessalonicenses"},
    )
    rows = [" & ".join([str(sunday), *(cycle.get(sunday, "»") for cycle in cycles)]) + r" \\"
            for sunday in range(2, 34)]
    return r"""
\phantomsection
\addcontentsline{toc}{section}{Ordinatio secundæ lectionis in dominicis « per annum »}
{\centering\fontsize{15pt}{19pt}\selectfont\bfseries
Tabella II\\
Ordinatio secundæ lectionis in dominicis «~per annum~»\par}
\medskip
\begin{BookCalendarTable}
\fontsize{11pt}{14.8pt}\selectfont
\arrayrulecolor{black}
\setlength{\tabcolsep}{0pt}
\noindent\begin{tabular}{@{}W{c}{.12\linewidth}*{3}{|W{c}{\dimexpr(.88\linewidth-3\arrayrulewidth)/3\relax}}@{}}
\BookCalendarOuterRule
\rule[-6pt]{0pt}{21pt}\textbf{Dominica} & \textbf{Anno A} & \textbf{Anno B} & \textbf{Anno C} \\
\hline
""" + "\n".join(rows) + r"""
\BookCalendarOuterRule
\end{tabular}
\par\end{BookCalendarTable}
\clearpage
"""


def missale_groups():
    return [
        [
            ("Tempus Nativitatis", ["Dominica II post Nativitatem", "Baptisma Domini"]),
            ("Tempus Quadragesimæ", ["Feria IV Cinerum"] +
             [f"Dominica {roman(n)} Quadragesimæ" for n in range(1, 6)] +
             ["Dominica in Palmis"]),
            ("Tempus Paschale", ["Dominica Resurrectionis"] +
             [f"Dominica {roman(n)} Paschæ" for n in range(2, 7)] +
             ["Ascensio Domini", "Dominica VII Paschæ", "Dominica Pentecostes"]),
            ("Sollemnitates mobiles", ["Sanctissima Trinitas", "SS. Corpus et Sanguis Christi",
                                      "Sacratissimum Cor Iesu"]),
            ("Tempus « per annum »", [f"Dominica {roman(n)} per annum" for n in range(2, 10)]),
        ],
        [
            ("Tempus « per annum »", [f"Dominica {roman(n)} per annum" for n in range(10, 34)] +
             ["Christus Universorum Rex"]),
            ("Tempus Adventus", [f"Dominica {roman(n)} Adventus" for n in range(1, 5)]),
            ("Tempus Nativitatis", ["Sancta Familia"]),
        ],
    ]


def day_month(day, abbreviate=False, align=False):
    months = "Ia. Fe. Mr. Ap. M. I. Iu. Ag. St. Ot. Nv. Dc.".split() if abbreviate else MONTHS
    month = months[day.month - 1]
    if align:
        return rf"\BookCalendarDate{{{day.day}}}{{{month}}}"
    return f"{day.day}~{month}"


def missale_label(label):
    short = {
        "Dominica II post Nativitatem": r"Dom. 2\textsuperscript{a} p. Nat.",
        "Baptisma Domini": "Baptisma Dom.",
        "Dominica in Palmis": "Dom. in Palmis",
        "Dominica Resurrectionis": "Dom. Resurr.",
        "Ascensio Domini": "Ascensio Dom.",
        "Dominica Pentecostes": "Dom. Pentecostes",
        "Sanctissima Trinitas": "SS. Trinitas",
        "SS. Corpus et Sanguis Christi": "SS. Corp. et S. Chr.",
        "Sacratissimum Cor Iesu": "SS. Cordis Iesu",
        "Christus Universorum Rex": "D. N. I. C. Regis",
        "Sancta Familia": "S. Familia I. M. I.",
    }
    if label in short:
        return short[label]
    if label.startswith("Dominica "):
        _, numeral, season = label.split(maxsplit=2)
        ordinal = next(number for number in range(1, 34) if roman(number) == numeral)
        season = "Quadrag." if season == "Quadragesimæ" else season
        return rf"Dom. {ordinal}\textsuperscript{{a}} {season}"
    return label


def gregorian_easter(year):
    """Oudin's computus, as used in the Calendar project's calendar.jsx."""
    golden = year % 19
    century = year // 100
    epact = (century - century // 4 - (8 * century + 13) // 25
             + 19 * golden + 15) % 30
    moon = epact - (epact // 28) * (1 - (29 // (epact + 1)) * ((21 - golden) // 11))
    weekday = (year + year // 4 + moon + 2 - century + century // 4) % 7
    offset = moon - weekday
    month = 3 + (offset + 40) // 44
    return date(year, month, offset + 28 - 31 * (month // 4))


def missale_pattern(easter):
    # Weekday alignment and month/day of Easter determine the movable cycle.
    # Leap status is included because the printed columns distinguish it.
    year = easter.year
    return isleap(year), date(year, 1, 1).weekday(), easter.month, easter.day


def missale_appendix(easters):
    years = [day.year for day in easters]
    calendars = [calendar(day) for day in easters]
    patterns = {missale_pattern(day): day.year for day in easters}
    matching_years = {}
    for year in range(years[-1] + 1, 2056):
        base = patterns.get(missale_pattern(gregorian_easter(year)))
        if base is not None:
            matching_years[base] = year
    pages = []
    for number, groups in enumerate(missale_groups(), 1):
        title = ""
        if number == 1:
            title = (
                r"\phantomsection\addcontentsline{toc}{section}{Tabula omnium dominicarum "
                r"necnon sollemnitatum et festorum mobilium}"
                r"\fontsize{15pt}{19pt}\selectfont\bfseries"
                r" Tabula omnium dominicarum necnon sollemnitatum et festorum mobilium\\"
                rf"ab anno {years[0]} usque ad annum {years[-1]}"
            )
        leading = "13.1pt" if number == 1 else "14.1pt"
        adjusted_rows = 0 if number == 1 else sum(1 + len(labels) for _, labels in groups)
        calendar_table = table(years, calendars, groups, abbreviate=True, matching_years=matching_years)
        notes = ""
        if number == 1:
            notes = r"""
\par\medskip
\textit{Litteræ italicæ}: dominica impedita. \quad
—: dominica deest. \quad \textsuperscript{b} Annus bissextilis.
\par """ + CALENDAR_NOTE + "\n"
        pages.append(rf"""
\BookMissaleTitle{{{title}}}
\begin{{BookCalendarTable}}
\fontsize{{11pt}}{{{leading}}}\selectfont
\BookMissaleTable{{{adjusted_rows}}}{{%{calendar_table}}}
""" + notes + r"""
\par\end{BookCalendarTable}
\clearpage
""")
    return r"\BookOpenLeft" + "\n" + "\n".join(pages)


CALENDAR_NOTE = (
    "Calendarium Romanum generale. Epiphania die 6 ianuarii, "
    "Ascensio et SS. Corpus Christi feria V."
)
