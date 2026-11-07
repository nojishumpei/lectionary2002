#!/usr/bin/env python3
"""Build the lectern and Gospel books from the canonical reading files."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from hashlib import sha256
from itertools import groupby
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from book_calendar import CALENDAR_NOTE, day_month, gregorian_easter, missale_appendix, second_reading_table
from book_titles import CELEBRATION_SUBTITLES, CELEBRATION_TITLE_BREAKS, PART_TITLE_BREAKS

BOOKS = Path(__file__).resolve().parent
LAYOUT = BOOKS / "layout"
ROOT = BOOKS.parent
ORDINARY_TIME_PART = "Tempus « Per Annum »"
PDF_LINK = re.compile(r"\(files/([\w/-]+)\.pdf\)")
CHANT_SNIPPET = re.compile(r"^\\gabcsnippet\{(.*?)^\}", re.M | re.S)
CONCLUSION_INPUT = re.compile(
    r"^(?:\\nopagebreak(?:\[[0-4]\])?[ \t]*\n[ \t]*)?"
    r"\\input\{\.\./common/(concg?[12])\}[ \t]*$", re.M)
CONCLUSION_NAMES = ("conc1", "conc2", "concg1", "concg2")
FINAL_DIVISION = re.compile(r"(\S+)\s+\(([:;]+)(?:[a-m]\+)?\)$")
PULPIT_TONES = ("Tonus Evangelii", "Tonus ad libitum", "Tonus Antiquior")
GOSPEL_INTRO_FILES = {f"{name}_{tone}.tex" for name in ("matt", "mark", "luke", "john")
                      for tone in ("a", "e", "l")}
GOSPEL_INTRO_BAR = re.compile(r"\(::\)(?=[ \t]*\n[^\n]*<sp>V/</sp>[^\n]*(?:Lé|In|Con)\(h\))")


def metadata(source, field):
    match = re.search(rf"^\\{field}\{{([^}}]*)\}}", source, re.M)
    return match[1] if match else ""


def catalogue_rows():
    part = ""
    temporal = False
    for line in (ROOT / "index.md").read_text(encoding="utf-8").splitlines():
        if line == "## Fontes":
            break
        if line.startswith("## "):
            temporal = line == "## Proprium de Tempore"
            part = line[3:]
        elif line.startswith("### ") and temporal:
            part = line[4:]
        elif line.startswith("|"):
            yield part, temporal, PDF_LINK.findall(line)


def catalogue():
    sources = {}
    for path in (ROOT / "files").glob("*/*.tex"):
        source = path.read_text(encoding="utf-8")
        kind = metadata(source, "readingtype")
        key = path.relative_to(ROOT / "files").with_suffix("").as_posix()
        funeral = path.parent.name == "DE"
        if not kind or kind == "Evangelium" or path.parent.name == "VO":
            continue
        # Saints Joachim and Anne is a local solemnity in Detroit.
        if key in {"SA/sjaot", "SA/sjaep"}:
            continue
        sources[key] = (metadata(source, "title"), metadata(source, "massdesignation"),
                        metadata(source, "yearcycle"), kind if funeral else "")

    parts = {}
    seen = set()
    for part, temporal, links in catalogue_rows():
        for key in links:
            if key in sources and key not in seen:
                parts.setdefault((part, temporal), []).append(key)
                seen.add(key)

    if missing := sources.keys() - seen:
        raise ValueError(f"Readings missing from catalogue: {sorted(missing)}")

    # The catalogue aligns the Epistle with the first Vigil row. In the
    # extended Vigil it follows all four Old Testament readings.
    easter = parts["Triduum Paschale et Tempus Paschale", True]
    easter.remove("EA/pvgep")
    easter.insert(easter.index("EA/pv4ot") + 1, "EA/pvgep")

    for (part, temporal), keys in parts.items():
        groups = []
        for (title, mass, cycle, funeral_kind), readings in groupby(keys, sources.__getitem__):
            group = list(readings)
            badge = cycle or ("ABC" if temporal else "")
            command = rf"\BookYear{{{badge}}}" if badge else r"\BookReadings"
            directive = rf"\BookDay{{{command}{{{','.join(group)}}}}}"
            if funeral_kind:
                qualifier = (mass or "Extra Tempus Paschale") if funeral_kind == "Lectio Prima" else ""
                title = f"{funeral_kind} {qualifier}".rstrip()
                directive = rf"\BookFuneralSection{{{funeral_kind}}}{{{qualifier}}}" + "\n" + directive
            groups.append((group, directive, title))
        yield part, groups


def book_reading(source, conclusions, *, pulpit=False):
    snippets = list(CHANT_SNIPPET.finditer(source))
    if not snippets:
        raise ValueError("Reading has no main chant snippet")
    main = snippets[-1]
    opening = source[:main.start(1)]
    if pulpit and len(snippets) > 1:
        # Christmas Day, Ascension, and some short forms engrave their own
        # announcement instead of loading a shared evangelist introduction.
        intro = snippets[0]
        opening = (opening[:intro.start()] + r"\BookGospelOpening{" +
                   pulpit_intro(intro[1]) + "}" + opening[intro.end():])
    music = main[1].rstrip()
    ending = source[main.end(1):]
    if dialogue := CONCLUSION_INPUT.search(ending):
        # Mask TeX comments so an optional verse cannot supply the last word.
        active = re.sub(r"(?<!\\)%[^\n]*", lambda match: " " * len(match[0]), music)
        division = FINAL_DIVISION.search(active.rstrip())
        if not division:
            raise ValueError("Expected a final division before the closing dialogue")
        # The existing division stays, while its custos is unnecessary in
        # one continuous score. Keep the last word and both replies together.
        reply = conclusions[dialogue[1]]
        # Some Gospel conclusions explicitly restate the clef because they
        # are separate scores in the individual PDFs.
        if clef := re.match(r"\([cf]b?[1-4]\)\s*", reply):
            if not active.lstrip().startswith(clef[0].strip()):
                raise ValueError(f"Closing clef differs from the main score in {dialogue[1]}")
            reply = reply[clef.end():]
        reply, count = re.subn(r"(\([^()]*\)\s+\(::\))$", r"</nlba>\1", reply)
        if count != 1:
            raise ValueError(f"Expected a final double bar in {dialogue[1]}")
        music = (music[:division.start()] + f"<nlba>{division[1]} ({division[2]})\n" +
                 reply + " (z)" + music[division.end():])
        ending = CONCLUSION_INPUT.sub("", ending, count=1)
    else:
        music += " (z)"
    return opening + music + "\n" + ending


def catalogue_easters():
    line = next(line for line in (ROOT / "index.md").read_text(encoding="utf-8").splitlines()
                if "(files/EA/easac.pdf)" in line)
    easters = [date(int(year), int(month), int(day))
               for month, day, year in re.findall(r"(\d+)/\s*(\d+)/(\d{4})", line)]
    if [easter.year for easter in easters] != list(range(2026, 2040)):
        raise ValueError("Expected catalogue Easter dates for 2026–2039")

    return easters


def pulpit_intro(source):
    # Place an inline h custos at the double bar. Z- keeps the break ragged
    # and suppresses the automatic custos at the far edge of this staff.
    opening, count = GOSPEL_INTRO_BAR.subn("(::h+Z-)", source)
    if count != 1:
        raise ValueError("Expected one Gospel announcement beginning on h")
    return opening


def occurrence_table():
    """Use the catalogue's Easter dates and the general Roman calendar."""
    catalogue = catalogue_easters()
    if [gregorian_easter(day.year) for day in catalogue] != catalogue:
        raise ValueError("Computus disagrees with the catalogue")
    rows = []
    for year in range(2026, 2056):
        easter = gregorian_easter(year)
        epiphany = date(year, 1, 6)
        baptism = epiphany + timedelta(days=7 - (epiphany.weekday() + 1) % 7)
        ash = easter - timedelta(days=46)
        lent_eve = ash - timedelta(days=1)
        ascension = easter + timedelta(days=39)
        pentecost = easter + timedelta(days=49)
        resumed = pentecost + timedelta(days=1)
        advent_start = date(year, 11, 27)
        advent = advent_start + timedelta(days=(6 - advent_start.weekday()) % 7)
        before_week = 1 + (lent_eve - baptism).days // 7
        after_week = 34 - (advent - resumed).days // 7
        rows.append(" & ".join([
            str(year), "ABC"[(year - 2026) % 3],
            day_month(ash, abbreviate=True, align=True), day_month(easter, abbreviate=True, align=True), day_month(ascension, abbreviate=True, align=True),
            day_month(pentecost, abbreviate=True, align=True), day_month(lent_eve, abbreviate=True, align=True), rf"\BookCalendarWeek{{{before_week}}}",
            day_month(resumed, abbreviate=True, align=True), rf"\BookCalendarWeek{{{after_week}}}", day_month(advent, abbreviate=True, align=True),
        ]) + r" \\")
        if (year - 2026) % 3 == 2 and year < 2055:
            rows.append(r"\hline")
    return r"""
\section*{\fontsize{15pt}{19pt}\selectfont Tabella temporaria præcipuarum celebrationum anni liturgici}
\addcontentsline{toc}{section}{Tabella temporaria præcipuarum celebrationum anni liturgici}
\smallskip
\begin{BookCalendarTable}
\fontsize{11pt}{14.8pt}\selectfont
\noindent\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}c c cccc cc cc c@{}}
\BookCalendarOuterRule
 & & & & & & \multicolumn{4}{c}{Hebdomadæ « per annum »} & \\
\cline{7-10}
 & & & & & & \multicolumn{2}{c}{ante Quadr.} &
 \multicolumn{2}{c}{post temp. pasch.} & \\
\cline{7-8}\cline{9-10}
\BookCalendarTwoLineHeading{Anno}{Domini} &
\BookCalendarTwoLineHeading{Cyclus}{dominicalis} &
\BookCalendarTwoLineHeading{Dies}{Cinerum} &
\BookCalendarHeading{}{Pascha}{} & \BookCalendarHeading{}{Ascensio}{} &
\BookCalendarHeading{}{Pentecostes}{} &
\BookCalendarHeading{}{usque ad d.}{} & \BookCalendarHeading{}{ad hebd.}{} &
\BookCalendarHeading{}{a die}{} & \BookCalendarHeading{}{ab hebd.}{} &
\BookCalendarHeading{Dominica}{prima}{Adventus} \\
\noalign{\vskip 2pt}
\hline
""" + "\n".join(rows) + r"""
\BookCalendarOuterRule
\end{tabular*}
\par\medskip
""" + CALENDAR_NOTE + r"""
\par Cyclus dominicalis novus a Dominica I Adventus incipit.
\par\end{BookCalendarTable}
\clearpage
"""


def compile_tex(directory, source, env, chant=False):
    (directory / "book.tex").write_text(source, encoding="utf-8")
    for _ in range(4):
        with (directory / "compile.log").open("w") as output:
            result = subprocess.run(
                ["lualatex", "-halt-on-error", "-interaction=nonstopmode", "book.tex"],
                cwd=directory, env=env, stdout=output, stderr=subprocess.STDOUT,
            )
        log = (directory / "book.log").read_text(encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError(f"{directory}: {log[-2600:]}")
        if chant:
            rerun = "Line heights, variable brace lengths" in log
        else:
            rerun = "Rerun to get" in log or "Label(s) may have changed" in log
        if not rerun:
            return log
    raise RuntimeError(f"TeX did not converge in {directory}")


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-j", "--jobs", type=positive_int,
                        default=min(10, os.cpu_count() or 1),
                        help="parallel TeX jobs (default: up to 10)")
    parser.add_argument("--build-dir", type=Path,
                        help="build files and reusable cache (default: under build/ for the selected mode)")
    parser.add_argument("-o", "--output", type=Path,
                        help="destination PDF (default: under books/ for the selected mode)")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--lectern", action="store_true",
                        help="build the full lectern book as books/lectern.pdf (default)")
    modes.add_argument("--pulpit", action="store_true",
                        help="build the full Gospel book as books/pulpit.pdf")
    modes.add_argument("--lectern-sample", "--sample", dest="sample", action="store_true",
                        help="build a lectern proof as books/lectern-sample.pdf")
    modes.add_argument("--pulpit-sample", action="store_true",
                        help="build a Gospel proof as books/pulpit-sample.pdf")
    # Older commands may still pass this flag. Both books now include the dialogue.
    parser.add_argument("--include-dialogue", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--rebuild", action="store_true",
                        help="recompile every selected group, ignoring its cached PDF")
    parser.add_argument("--list", action="store_true", dest="list_readings",
                        help="list the selected readings without compiling or writing files")
    args = parser.parse_args(argv)
    name = "pulpit" if args.pulpit or args.pulpit_sample else "lectern"
    if args.sample or args.pulpit_sample:
        name += "-sample"
    args.build_dir = (args.build_dir or ROOT / "build" / name).resolve()
    args.output = (args.output or BOOKS / (name + ".pdf")).resolve()
    if args.output.suffix.lower() != ".pdf":
        parser.error("--output must name a PDF file")
    if ROOT / "files" in args.output.parents:
        parser.error("the book output cannot replace an individual reading PDF")
    if (args.build_dir in {ROOT, BOOKS, LAYOUT} or
            ROOT / "files" == args.build_dir or ROOT / "files" in args.build_dir.parents or
            LAYOUT in args.build_dir.parents):
        parser.error("--build-dir must be separate from the reading sources and book layout")
    return args


def selection(sample=False):
    sample_openers = {"AD/c01ot", "AD/a02ot"}
    parts = []
    number = 0
    for part, groups in catalogue():
        selected = []
        for keys, directive, title in groups:
            number += 1
            if not sample or keys[0] in sample_openers:
                selected.append((number, keys, directive, title))
        if selected:
            parts.append((part, selected))
    return parts


def pulpit_selection(sample=False):
    sources = {}
    for path in (ROOT / "files").glob("*/*.tex"):
        source = path.read_text(encoding="utf-8")
        if path.parent.name == "VO" or metadata(source, "readingtype") != "Evangelium":
            continue
        key = path.relative_to(ROOT / "files").with_suffix("").as_posix()
        title, mass, cycle, number = (metadata(source, field) for field in
                                      ("title", "massdesignation", "yearcycle", "readingnumber"))
        if (key.startswith("SA/sjag") or title == "Feria VI in Passione Domini" or
                (title == "Dominica in Palmis de Passione Domini" and mass != "Ad Processionem")):
            continue
        passage = tuple(metadata(source, field) for field in ("scriptureref", "readingform", "readingnote"))
        sources[key] = ((title, mass, cycle, number), passage, metadata(source, "tone"))

    ordered = {}
    seen = set()
    for part, temporal, links in catalogue_rows():
        for key in links:
            if key in sources and key not in seen:
                ordered.setdefault((part, temporal), []).append(key)
                seen.add(key)
    if missing := sources.keys() - seen:
        raise ValueError(f"Gospels missing from catalogue: {sorted(missing)}")

    sample_titles = {"Dominica I Adventus", "Dominica II Adventus", "Dominica XXXIII «~per annum~»"}
    parts = {}
    number = 0
    sample_cycles = {}
    for (part, temporal), ordered_keys in ordered.items():
        for (title, mass, cycle, reading_number), readings in groupby(ordered_keys, lambda key: sources[key][0]):
            if sample and title not in sample_titles:
                continue
            if sample:
                sample_cycles.setdefault(title, []).append(cycle)
            passages = {}
            for key in readings:
                _, passage, tone = sources[key]
                tones = passages.setdefault(passage, {})
                if tone in tones:
                    raise ValueError(f"Duplicate Gospel tone for {key}: {tone}")
                tones[tone] = key
            keys = []
            for (reference, _, _), tones in passages.items():
                if tones.keys() != set(PULPIT_TONES):
                    raise ValueError(f"Expected all three Gospel tones for {title}, {reference}")
                keys.extend(tones[tone] for tone in PULPIT_TONES)
            badge = cycle or ("ABC" if temporal else "")
            command = rf"\BookYear{{{badge}}}" if badge else r"\BookReadings"
            directive = rf"\BookDay{{{command}{{{','.join(keys)}}}}}"
            index_title = title
            if reading_number and keys[0].startswith("DE/"):
                label = f"N.~{reading_number}"
                index_title = label
                directive = rf"\BookFuneralSection{{{label}}}{{}}" + "\n" + directive
            number += 1
            parts.setdefault(part, []).append((number, keys, directive, index_title))
    if sample and sample_cycles != dict.fromkeys(sample_titles, ["A", "B", "C"]):
        raise ValueError("Expected all three cycles for the three sample Sundays")
    return list(parts.items())


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_book(args, parts, *, select=selection, assembly_dir=None, title_page=None):
    for program in ("lualatex", "gregorio"):
        if not shutil.which(program):
            raise RuntimeError(f"{program} is required; see MAINTENANCE.md")
    versions = {}
    for program in ("lualatex", "gregorio"):
        version = subprocess.check_output([program, "--version"], text=True)
        versions[program] = version.splitlines()[0]

    work = args.build_dir
    assembly_dir = assembly_dir or work
    assembly_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = f"{LAYOUT}{os.pathsep}{env.get('TEXINPUTS', '')}"
    staged = work / "files"
    common = staged / "common"
    common.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT / "index.md", Path(__file__).resolve(),
              BOOKS / "book_calendar.py", BOOKS / "book_titles.py",
              *sorted(LAYOUT.glob("*.tex")), LAYOUT / "book-grid.lua"]
    if title_page is not None:
        inputs.append(title_page)
    pulpit = args.pulpit or args.pulpit_sample
    sample = args.sample or args.pulpit_sample
    for path in sorted((ROOT / "files/common").glob("*.tex")):
        inputs.append(path)
        target = common / path.name
        if pulpit and path.name in GOSPEL_INTRO_FILES:
            try:
                opening = pulpit_intro(path.read_text(encoding="utf-8"))
            except ValueError as error:
                raise ValueError(f"{path.name}: {error}") from error
            target.write_text(opening, encoding="utf-8")
        else:
            shutil.copyfile(path, target)
    conclusions = {name: CHANT_SNIPPET.search((common / (name + ".tex")).read_text(encoding="utf-8"))[1].strip()
                   for name in CONCLUSION_NAMES}
    for _, groups in parts:
        for _, keys, _, _ in groups:
            for key in keys:
                path = ROOT / "files" / (key + ".tex")
                inputs.append(path)
                target = staged / (key + ".tex")
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    adapted = book_reading(path.read_text(encoding="utf-8"), conclusions, pulpit=pulpit)
                except ValueError as error:
                    raise ValueError(f"{key}: {error}") from error
                target.write_text(adapted, encoding="utf-8")
    hashes = {os.path.relpath(path, ROOT): file_hash(path) for path in inputs}

    preamble = (rf"\newcommand{{\LectionaryFiles}}{{{staged.as_posix()}}}" +
                "\n\\input{book-profile}\n")
    chapter = preamble + "\\input{book-layout}\n"
    if pulpit:
        chapter += "\\BookVolume{gospel}\n"
    chapter += r"""
\input{book-grid}
\input{book-running-heads}
\input{book-sections}
\input{book-cycle-badges}
"""
    if pulpit:
        chapter += "\\input{book-pulpit-heads}\n"
    chapter += r"""
\BookConfigureReadings
\fancyfoot{}
\begin{document}
"""
    book_title = "Evangelia in cantu" if pulpit else "Lectiones in cantu"
    master = preamble + rf"\newcommand{{\BookPDFTitle}}{{{book_title}}}" + r"""
\providecommand{\BookDayStart}{}
\providecommand{\BookDayPageMark}[1]{}
\input{book-running-heads}
\input{book-sections}
\input{book-calendar-tables}
\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}
\hypersetup{pdftitle={\BookPDFTitle},pdfauthor={Lectionary2002},
  pdfpagelayout=TwoPageRight,pdfstartview=Fit}
\newfontface\BookTitleSubtitleFont[Letters=SmallCaps]{MinionPro-Regular}
\renewcommand{\contentsname}{Index}
\setcounter{tocdepth}{2}
\protected\def\BookIndexSubtitleBreak{\newline}
\pdfstringdefDisableCommands{\def\BookIndexSubtitleBreak{ · }}
\renewcommand{\BookPartContents}[1]{\phantomsection\addcontentsline{toc}{section}{#1}}
\fancypagestyle{booknumber}{%
  \fancyhf{}
  \fancyfoot[LE,RO]{\fontsize{11}{13}\selectfont\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}
"""
    if pulpit and not sample:
        # The full volume needs room for four-digit index page numbers.
        master += r"""
\makeatletter
\renewcommand*{\@pnumwidth}{2.1em}
\renewcommand*{\@tocrmarg}{3.1em}
\makeatother
"""
    master += "\\begin{document}\n"
    if title_page is not None:
        master += (r"\includepdf[pages=1,noautoscale,pagecommand={\thispagestyle{empty}}]"
                   f"{{{os.path.relpath(title_page, assembly_dir)}}}\n")
    elif pulpit:
        master += r"""
\thispagestyle{empty}
\vspace*{\fill}
\begin{center}
  {\BookPartStyle EVANGELIA IN CANTU\par}
"""
        if sample:
            master += r"""
  \vspace{12pt}
  {\BookTitleSubtitleFont\fontsize{21pt}{26pt}\selectfont Specimen\par}
"""
        master += r"""
  \vspace{24pt}
  {\fontsize{16pt}{21pt}\selectfont Secundum Missale Romanum\par}
  {\fontsize{14pt}{18pt}\selectfont Editio typica tertia, reimpressio emendata\par}
  \vspace{10pt}
  {\fontsize{14pt}{18pt}\selectfont MMVIII\par}
\end{center}
\vspace*{\fill}
"""
    else:
        master += r"""
\thispagestyle{empty}
\vspace*{\fill}
\begin{center}
  {\BookPartStyle LECTIONES IN CANTU\par}
  \vspace{10pt}
  {\BookTitleSubtitleFont\fontsize{21pt}{26pt}\selectfont Lectiones Primæ et Secundæ\par}
  \vspace{22pt}
  {\fontsize{17pt}{22pt}\selectfont\itshape
    Pro dominicis, sollemnitatibus et festis\\
    necnon pro Missis defunctorum\par}
  \vspace{22pt}
  {\fontsize{16pt}{21pt}\selectfont Secundum Missale Romanum\par}
  {\fontsize{14pt}{18pt}\selectfont Editio typica tertia, reimpressio emendata\par}
  \vspace{10pt}
  {\fontsize{14pt}{18pt}\selectfont MMVIII\par}
\end{center}
\vspace*{\fill}
"""
    master += r"""
\BookOpenRight
\pagestyle{booknumber}\tableofcontents\clearpage
"""
    master += occurrence_table()
    if not pulpit and (sample or any(part == ORDINARY_TIME_PART for part, _ in parts)):
        master += second_reading_table()
    jobs = []
    for part, groups in parts:
        indexed = set()
        cover = PART_TITLE_BREAKS.get(part)
        cover_option = f"[{cover}]" if cover is not None and cover != part else ""
        master += rf"\BookPart{cover_option}{{{part}}}" + "\n"
        for number, keys, directive, title in groups:
            # Stable names preserve cached groups when earlier catalogue rows change.
            directory = work / "groups" / keys[0].replace("/", "-")
            directory.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(LAYOUT / "book-grid.lua", directory / "book-grid.lua")
            display = CELEBRATION_TITLE_BREAKS.get(title)
            subtitle = CELEBRATION_SUBTITLES.get(title)
            body = directive
            if display is not None and display != title:
                body = rf"\renewcommand{{\BookCelebrationTitle}}[1]{{{display}}}" + "\n" + body
            if subtitle:
                body = rf"\renewcommand*{{\BookCelebrationSubtitle}}{{{subtitle}}}" + "\n" + body
            jobs.append((directory, keys, chapter + body + "\n\\end{document}\n"))
            toc = ""
            if title not in indexed:
                index_title = title
                if subtitle:
                    index_title += r"\BookIndexSubtitleBreak{}" + subtitle
                toc = rf",addtotoc={{1,subsection,2,{{{index_title}}},day-{number}}}"
                indexed.add(title)
            relative = os.path.relpath(directory, assembly_dir)
            master += (r"\includepdf[pages=-,noautoscale,pagecommand={\thispagestyle{booknumber}}" +
                       f"{toc}]{{{relative}/book.pdf}}\n")
    count = sum(len(keys) for _, keys, _ in jobs)
    print(f"Building {count} readings in {len(jobs)} groups.", flush=True)

    shared = sha256(json.dumps(versions, sort_keys=True).encode())
    for path in sorted([*LAYOUT.glob("*.tex"), LAYOUT / "book-grid.lua", *common.glob("*.tex")]):
        shared.update(path.name.encode())
        shared.update(path.read_bytes())

    def build(job):
        directory, keys, source = job
        fingerprint = shared.copy()
        fingerprint.update(source.encode())
        for key in keys:
            fingerprint.update((staged / (key + ".tex")).read_bytes())
        digest = fingerprint.hexdigest()
        stamp = directory / "complete.json"
        pdf = directory / "book.pdf"
        if not args.rebuild and pdf.is_file() and stamp.is_file():
            try:
                previous = json.loads(stamp.read_text(encoding="utf-8"))
                if (previous.get("fingerprint") == digest and previous.get("readings") == keys and
                        previous.get("pdf_sha256") == file_hash(pdf)):
                    return {"readings": keys, "reused": True, "pdf_sha256": previous["pdf_sha256"]}
            except (ValueError, OSError):
                pass
        stamp.unlink(missing_ok=True)
        log = compile_tex(directory, source, env, chant=True)
        if re.findall(r"^BOOK-HEADING: (\S+);", log, re.M) != keys:
            raise RuntimeError(f"Reading headings differ from catalogue in {directory}")
        pdf_hash = file_hash(pdf)
        write_json(stamp, {"fingerprint": digest, "readings": keys, "pdf_sha256": pdf_hash})
        return {"readings": keys, "reused": False, "pdf_sha256": pdf_hash}

    results, failures = [], []
    jobs.sort(key=lambda job: sum((staged / (key + ".tex")).stat().st_size for key in job[1]), reverse=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for processed, future in enumerate(as_completed([pool.submit(build, job) for job in jobs]), 1):
            try:
                results.append(future.result())
            except (RuntimeError, OSError) as error:
                failures.append(str(error))
                print(error, file=sys.stderr, flush=True)
            if processed % 10 == 0 or processed == len(jobs):
                print(f"{processed}/{len(jobs)} groups processed.", flush=True)
    if failures:
        write_json(assembly_dir / "build-report.json", {"status": "failed", "failures": failures})
        raise RuntimeError(f"{len(failures)} groups failed; see logs under {work / 'groups'}")

    master += missale_appendix(catalogue_easters()[:9]) + "\\end{document}\n"
    assembly = shared.copy()
    assembly.update(master.encode())
    if title_page is not None:
        assembly.update(hashes[os.path.relpath(title_page, ROOT)].encode())
    for directory, _, _ in sorted(jobs, key=lambda job: str(job[0])):
        assembly.update(str(directory.relative_to(work)).encode())
        assembly.update(file_hash(directory / "book.pdf").encode())
    assembly_digest = assembly.hexdigest()
    assembly_stamp = assembly_dir / "assembly.json"
    master_pdf = assembly_dir / "book.pdf"
    master_reused = False
    if not args.rebuild and master_pdf.is_file() and assembly_stamp.is_file():
        try:
            previous = json.loads(assembly_stamp.read_text(encoding="utf-8"))
            master_reused = (previous.get("fingerprint") == assembly_digest and
                             previous.get("pdf_sha256") == file_hash(master_pdf))
        except (ValueError, OSError):
            pass
    if not master_reused:
        assembly_stamp.unlink(missing_ok=True)
        compile_tex(assembly_dir, master, env)
        write_json(assembly_stamp, {"fingerprint": assembly_digest,
                                    "pdf_sha256": file_hash(master_pdf)})
    changed = [rel for rel, digest in hashes.items() if file_hash(ROOT / rel) != digest]
    if changed:
        raise RuntimeError("Inputs changed during the build; rebuild before publishing: " + ", ".join(changed))
    if select(sample) != parts:
        raise RuntimeError("The reading selection changed during the build; run the builder again")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_unchanged = args.output.is_file() and file_hash(args.output) == file_hash(master_pdf)
    if args.output != master_pdf and not output_unchanged:
        temporary = args.output.with_suffix(".pdf.tmp")
        shutil.copyfile(master_pdf, temporary)
        temporary.replace(args.output)
    report = {"status": "complete", "readings": count, "groups": len(jobs),
              "rebuilt_groups": sum(not r["reused"] for r in results),
              "reused_groups": sum(r["reused"] for r in results),
              "assembly_reused": master_reused, "output_unchanged": output_unchanged,
              "sample": sample,
              "tools": versions, "input_sha256": hashes,
              "output_sha256": file_hash(args.output), "group_results": results}
    write_json(assembly_dir / "build-report.json", report)
    print(f"Saved {args.output}", flush=True)
    print(f"Rebuilt {report['rebuilt_groups']} groups; reused {report['reused_groups']}.", flush=True)
    return 0


def main(argv=None):
    args = arguments(argv)
    try:
        select = pulpit_selection if args.pulpit or args.pulpit_sample else selection
        parts = select(args.sample or args.pulpit_sample)
        if args.list_readings:
            for part, groups in parts:
                print(part)
                for _, keys, _, _ in groups:
                    for key in keys:
                        reference = metadata((ROOT / "files" / (key + ".tex")).read_text(encoding="utf-8"), "scriptureref")
                        print(f"  {key}  {reference.replace('~', ' ').replace('--', '–')}")
            print(f"{sum(len(keys) for _, groups in parts for _, keys, _, _ in groups)} readings selected.")
            return 0
        return build_book(args, parts, select=select)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
