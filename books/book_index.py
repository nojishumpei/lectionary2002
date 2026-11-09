"""Scripture lookup tables for the printed and digital chant books."""
from itertools import groupby
import re

# The order of the Nova Vulgata, using the sigla found in the chant sources.
BIBLE_BOOKS = {
    "Gen": "Genesis", "Ex": "Exodus", "Lev": "Leviticus", "Num": "Numeri",
    "Deut": "Deuteronomium", "Ios": "Iosue", "Iudic": "Iudicum", "Ruth": "Ruth",
    "1 Sam": "I Samuelis", "2 Sam": "II Samuelis", "1 Reg": "I Regum",
    "2 Reg": "II Regum", "1 Chr": "I Paralipomenon", "2 Chr": "II Paralipomenon",
    "Esd": "Esdras", "Neh": "Nehemias", "Tob": "Tobias", "Iudt": "Iudith",
    "Est": "Esther", "Iob": "Iob", "Ps": "Psalmi", "Prov": "Proverbia",
    "Qoh": "Ecclesiastes", "Cant": "Canticum Canticorum", "Sap": "Sapientia",
    "Sir": "Ecclesiasticus", "Is": "Isaias", "Ier": "Ieremias",
    "Lam": "Lamentationes", "Bar": "Baruch", "Ez": "Ezechiel", "Dan": "Daniel",
    "Os": "Osee", "Ioel": "Ioel", "Am": "Amos", "Abd": "Abdias", "Ion": "Ionas",
    "Mic": "Michæas", "Nah": "Nahum", "Hab": "Habacuc", "Soph": "Sophonias",
    "Ag": "Aggæus", "Zac": "Zacharias", "Mal": "Malachias",
    "1 Mac": "I Maccabæorum", "2 Mac": "II Maccabæorum",
    "Mt": "Matthæus", "Mc": "Marcus", "Lc": "Lucas", "Io": "Ioannes",
    "Act": "Actus Apostolorum", "Rom": "Ad Romanos", "1 Cor": "I ad Corinthios",
    "2 Cor": "II ad Corinthios", "Gal": "Ad Galatas", "Eph": "Ad Ephesios",
    "Phil": "Ad Philippenses", "Col": "Ad Colossenses", "1 Th": "I ad Thessalonicenses",
    "2 Th": "II ad Thessalonicenses", "1 Tim": "I ad Timotheum", "2 Tim": "II ad Timotheum",
    "Tit": "Ad Titum", "Phm": "Ad Philemonem", "Hebr": "Ad Hebræos", "Iac": "Iacobi",
    "1 Petr": "I Petri", "2 Petr": "II Petri", "1 Io": "I Ioannis", "2 Io": "II Ioannis",
    "3 Io": "III Ioannis", "Iud": "Iudæ", "Ap": "Apocalypsis",
}
BOOK_ORDER = {book: number for number, book in enumerate(BIBLE_BOOKS)}


def scripture_reference(reference):
    text = reference.replace("~", " ").replace("--", "–")
    match = re.fullmatch(r"((?:[1-3] )?[A-Za-z]+) +(\d.*)", text)
    if not match or match[1] not in BOOK_ORDER:
        raise ValueError(f"Unrecognized Scripture reference: {reference}")
    book, passage = match.groups()
    return book, passage.replace("—", "–")


def scripture_sort(reference):
    book, passage = reference
    numbers = tuple((int(number), part) for number, part in re.findall(r"(\d+)([a-z]?)", passage))
    return BOOK_ORDER[book], numbers, passage


def index_context(key, fields, cycle, *, pulpit):
    title, mass, number, kind, form, note = fields
    if key.startswith("DE/") and kind == "Lectio Prima" and not mass:
        mass = "Extra Tempus Paschale"
    if number:
        kind += f" N.~{number}"
    cycle = {"": "", "ABC": "A, B et C"}.get(cycle, cycle)
    return r"~\textperiodcentered\ ".join(
        value for value in (title, mass, cycle, "" if pulpit and not number else kind,
                            form, note.lower()) if value
    )


INDEX_OPENING = r"""
\BookOpenRight
\section*{Index lectionum}
\addcontentsline{toc}{section}{Index lectionum}
"""


def scripture_index(locations, *, tones=(), volume=""):
    """Typeset one index, with links for readings present in this PDF."""
    entries = {}
    for reference, context, tone, reading_volume, page in locations:
        occurrence = (reading_volume, context)
        entries.setdefault(reference, {}).setdefault(occurrence, {}).setdefault(tone, []).append(page)

    def locator(reading_volume, page):
        display = f"{reading_volume},~{page}" if reading_volume else str(page)
        if reading_volume == volume:
            return rf"\hyperlink{{page.{page}}}{{{display}}}"
        return display

    headers = ((r"\shortstack[r]{Tonus\\Evangelii}", r"\shortstack[r]{Tonus\\ad libitum}",
                r"\shortstack[r]{Tonus\\Antiquior}") if tones else
               (("Vol.,~pag.",) if volume else ("Pagina",)))
    widths = [".19", ".534", ".092", ".092", ".092"] if tones else [".22", ".67", ".11"]
    column_padding = "3pt" if tones else "5pt"
    # The interior columns carry the full intercolumn spacing.
    columns = [r">{\raggedright\arraybackslash}p{" + widths[0] + r"\linewidth}"]
    columns.append(r">{\raggedright\arraybackslash}p{\dimexpr " + widths[1] +
                   rf"\linewidth-{2 * (len(widths) - 1)}\tabcolsep\relax" + "}")
    columns.extend(r">{\raggedleft\arraybackslash}p{" + width + r"\linewidth}" for width in widths[2:])
    header = " & ".join(r"\textbf{" + label + "}" for label in ("Locus", "Celebratio", *headers))
    lines = [
        r"\begingroup",
        r"\fontsize{11pt}{13.5pt}\selectfont\addfontfeatures{Numbers=Lining}",
        rf"\setlength{{\tabcolsep}}{{{column_padding}}}\setlength{{\LTpre}}{{0pt}}",
        r"\begin{longtable}{@{}" + "".join(columns) + "@{}}",
        header + r" \\ \hline \endhead",
    ]
    for book, references in groupby(sorted(entries, key=scripture_sort), key=lambda ref: ref[0]):
        lines.append(rf"\multicolumn{{{len(widths)}}}{{@{{}}l}}{{\rule{{0pt}}{{18pt}}"
                     rf"\textbf{{\scshape {BIBLE_BOOKS[book]}}}}} \\*")
        for reference in references:
            label = book.replace(" ", "~") + "~" + reference[1].replace("–", "--")
            occurrences = entries[reference]
            for position, ((reading_volume, context), pages) in enumerate(occurrences.items()):
                row = [label if position == 0 else "", context]
                for tone in tones or ("",):
                    row.append(", ".join(locator(reading_volume, page) for page in dict.fromkeys(pages[tone])))
                lines.append(" & ".join(row) + (r" \\*" if position + 1 < len(occurrences) else r" \\"))
    lines.extend([r"\end{longtable}", r"\endgroup", ""])
    return "\n".join(lines)
