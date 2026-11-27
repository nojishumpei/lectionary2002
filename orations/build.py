#!/usr/bin/env python3
"""Refresh oration Textus and catalogue tables from the checked-in TeX scores.

Prayer fragments supply the text; individual wrappers supply heading fields;
Mass print wrappers supply prayer order and page layout. See MAINTENANCE.md.
Only changed outputs are written, preserving incremental PDF builds.
"""
from pathlib import Path
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRINT_TYPE = "Orationes ad Missam"
BLOCK = re.compile(r"^<!-- orations:([^\s:]+):start -->.*?"
                   r"^<!-- orations:\1:end -->", re.M | re.S)


def arguments(source, command, count):
    """Read balanced TeX arguments, preserving the exact chant content."""
    source = re.sub(r"(?m)(?<!\\)%[^\n]*", "", source)
    match = re.search(r"\\" + command + r"\s*\{", source)
    if not match:
        raise ValueError(f"Missing {command}")
    pos = match.end() - 1
    result = []
    for _ in range(count):
        while pos < len(source) and source[pos].isspace():
            pos += 1
        if pos == len(source) or source[pos] != "{":
            raise ValueError(f"Missing argument of {command}")
        start = pos = pos + 1
        depth = 1
        while pos < len(source) and depth:
            if source[pos] == "{" and source[pos - 1] != "\\":
                depth += 1
            elif source[pos] == "}" and source[pos - 1] != "\\":
                depth -= 1
            pos += 1
        if depth:
            raise ValueError(f"Unclosed argument of {command}")
        result.append(source[start:pos - 1].strip())
    return result


def plain_text(gabc):
    # Preserve printed parentheses around optional words before stripping notes.
    gabc = gabc.replace(r"<v>\textnormal{(}</v>", "\ue000")
    gabc = gabc.replace(r"<v>\textnormal{)}</v>", "\ue001")
    gabc = gabc.replace("<nlba>", "").replace("</nlba>", "")
    text = re.sub(r"\([^)]*\)", "", gabc)
    if any(c in text for c in "{}\\<>"):
        raise ValueError("Textus needs explicit handling for GABC/TeX markup")
    return re.sub(r"\s+", " ", text).strip().replace("\ue000", "(").replace("\ue001", ")")


def scores(root):
    """Read the same wrappers latexmk builds, without a separate manifest."""
    result = {}
    fragments = {p.relative_to(root / "files/orations").as_posix()
                 for p in (root / "files/orations").glob("*/*.inc.tex")}
    for path in sorted((root / "files").glob("*/*.tex")):
        source = re.sub(r"(?m)(?<!\\)%[^\n]*", "", path.read_text())
        if not re.search(r"\\orationtype\s*\{", source):
            continue
        key = path.relative_to(root / "files").with_suffix("").as_posix()
        fields = {}
        for name in ("title", "orationtype", "tone", "massdesignation", "readingform"):
            fields[name] = (arguments(source, name, 1)[0]
                            if re.search(r"\\" + name + r"\s*\{", source) else "")
        if not all(fields[name] for name in ("title", "orationtype", "tone")):
            raise ValueError(f"Missing oration heading fields: {key}")
        inputs = re.findall(r"\\input\{\.\./orations/([^{}]+\.inc\.tex)\}", source)
        if not inputs or any(name not in fragments for name in inputs):
            raise ValueError(f"Missing or invalid prayer input: {key}")
        if fields["orationtype"] != PRINT_TYPE and len(inputs) != 1:
            raise ValueError(f"Individual prayer must input one fragment: {key}")
        result[key] = dict(id=key, inputs=inputs, **fields)
    represented = {name for score in result.values() if score["orationtype"] != PRINT_TYPE
                   for name in score["inputs"]}
    if fragments - represented:
        raise ValueError("Prayer fragments without individual wrappers: " + ", ".join(sorted(fragments - represented)))
    if not result:
        raise ValueError("No oration wrappers found")
    return result


def collection(root):
    """Use marked catalogue entries to associate each Mass with its print score."""
    wrappers = scores(root)
    by_fragment = {}
    for key, score in wrappers.items():
        if score["orationtype"] != PRINT_TYPE:
            by_fragment.setdefault(score["inputs"][0], []).append(key)
    index = (root / "index.md").read_text()
    seen, ordered, blocks = set(), [], set()

    def replace(match):
        mass_id = match[1]
        if mass_id in blocks:
            raise ValueError(f"Duplicate oration catalogue block: {mass_id}")
        blocks.add(mass_id)
        headings = re.findall(r"(?m)^(#+) \[Orationes\]\(files/([^()\s]+)\.pdf\)$", match[0])
        if len(headings) != 1:
            raise ValueError(f"Expected one Orationes print heading in {mass_id}")
        level, print_key = headings[0]
        if print_key not in wrappers or wrappers[print_key]["orationtype"] != PRINT_TYPE:
            raise ValueError(f"Missing Mass print wrapper: {print_key}")
        if print_key in seen:
            raise ValueError(f"Mass print linked in multiple catalogue blocks: {print_key}")
        prayer_keys = []
        for fragment in dict.fromkeys(wrappers[print_key]["inputs"]):
            if fragment not in by_fragment:
                raise ValueError(f"No individual prayer wrapper for {fragment}")
            prayer_keys.extend(by_fragment[fragment])
        columns = list(dict.fromkeys(wrappers[key]["orationtype"] for key in prayer_keys))
        rows = [f"<!-- orations:{mass_id}:start -->", "",
                f"{level} [Orationes](files/{print_key}.pdf)", "",
                "| " + " | ".join(columns) + " |",
                "| " + " | ".join("---" for _ in columns) + " |"]
        cells = []
        for title in columns:
            links = []
            for key in prayer_keys:
                score = wrappers[key]
                if score["orationtype"] != title:
                    continue
                link = f'[{score["tone"]}](files/{key}.pdf)'
                if score["readingform"]:
                    link = f'<span class="reading-form">{score["readingform"]}</span><br>' + link
                links.append(link)
            cells.append("<br>".join(links))
        rows += ["| " + " | ".join(cells) + " |", "", f"{level} Lectiones", "",
                 f"<!-- orations:{mass_id}:end -->"]
        for key in prayer_keys + [print_key]:
            if key not in seen:
                ordered.append(wrappers[key])
                seen.add(key)
        return "\n".join(rows)

    index = BLOCK.sub(replace, index)
    starts = re.findall(r"(?m)^<!-- orations:([^\s:]+):start -->", index)
    ends = re.findall(r"(?m)^<!-- orations:([^\s:]+):end -->", index)
    if len(starts) != len(blocks) or len(ends) != len(blocks):
        raise ValueError("Unpaired or duplicate oration catalogue markers")
    if set(wrappers) - seen:
        raise ValueError("Oration wrappers missing from catalogue blocks: " + ", ".join(sorted(set(wrappers) - seen)))
    return index, ordered


def build(root):
    index, ordered = collection(root)
    records = {}
    for score in ordered:
        if score["orationtype"] == PRINT_TYPE:
            continue
        key = score["id"]
        source = (root / "files/orations" / score["inputs"][0]).read_text()
        blocks = list(re.finditer(r"\\orationcontent\s*\{", source))
        if not blocks:
            raise ValueError(f"Missing prayer content: {key}")
        parts = []
        for i, block in enumerate(blocks):
            invitation, body = arguments(source[block.start():], "orationcontent", 2)
            text = plain_text(body)
            if not invitation.startswith("(c4)") or not text or re.search(r"Orémus|Inclináte", text):
                raise ValueError(f"Invalid prayer content: {key}")
            if i:
                parts.append("Vel:")
            parts.extend(re.split(r" (?=(?:Per Dóminum|Per Christum|Qui tecum|Qui vivis|Qui vivit)\b)", text))
        records[key] = dict(id=key, kind="oration", celebration=score["title"].upper(),
                            reading=score["orationtype"], year="", reference="", number="",
                            mass=score["massdesignation"], form=score["readingform"],
                            tone=score["tone"], intro="", paragraphs=parts, pdfs=[key + ".pdf"])
    return {"index.md": index,
            "assets/data/orations.json": json.dumps(records, ensure_ascii=False, indent=2) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated outputs without writing")
    parser.add_argument("--list-pdfs", action="store_true", help="List PDF targets relative to files/")
    args = parser.parse_args()
    try:
        if args.list_pdfs:
            print(" ".join(score["id"] + ".pdf" for score in collection(ROOT)[1]))
            return
        outputs = build(ROOT)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    changed = []
    for name, content in outputs.items():
        path = ROOT / name
        if not path.exists() or path.read_text() != content:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
    if args.check and changed:
        parser.error("Outdated generated files: " + ", ".join(changed))
    print(f'{len(changed)} generated files {"need updates" if args.check else "updated"}.')


if __name__ == "__main__":
    main()
