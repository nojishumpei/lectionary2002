# Maintenance notes

Technical reference for transcribing, compiling, and maintaining the collection.

## Building the scores

The scores require LuaLaTeX, GregorioTeX, latexmk, Make, and an installed copy of Minion Pro. The font is not included.

From the repository root, check and build all readings with up to ten concurrent jobs, or build a single reading:

```sh
make -C files -j10
make -C files AD/a01ep.pdf
```

The Makefile lets latexmk check each reading’s recorded inputs, including shared introductions and the preamble. Unchanged documents do not run LuaLaTeX. The first build in a fresh checkout establishes these records and may recompile existing PDFs. Keep the auxiliary records for incremental builds.

Use `make -C files -j10 rebuild` to force compilation of all readings. `make -C files clean` removes auxiliary records while preserving PDFs and sources; run cleanup separately from builds. For a direct manual build, run `lualatex a01ep.tex` from `files/AD`.

## Reading headings

Each reading stores its heading fields separately. For example:

```latex
\title{Dominica XXVIII «~per annum~»}
\readingtype{Evangelium}
\yearcycle{A}
\scriptureref{Mt~22:1--10}
\tone{Tonus Antiquior}
\readingform{Forma Brevior}
```

`files/common/preamble.tex` controls the presentation: the celebration title is uppercase in `\small`, the reading designation is in `\large\bfseries`, and the supporting details and red reference are in `\small`. The year is printed as `Anno A`; the supporting line places the tone before the reading form. Empty optional fields are omitted, including their separators.

Use `\massdesignation{Ad Missam in Vigilia}` for a particular Mass, `\readingnumber{13}` for a sequential reading option (printed as `N. 13`), and `\readingnote{Ad Libitum}` for an additional qualification. These fields are independent of the year cycle. A shorter reading uses `\readingform{Forma Brevior}` even when no chant tone is specified.

Scriptural references use the Latin book abbreviations from the *Ordo lectionum Missæ*, a colon between chapter and verse, an en dash (`--` in TeX) for a range, and lowercase verse-part letters: `Gen~22:1--2, 9a, 10--13, 15--18`. The `~` keeps a book abbreviation with its reference. Reading selections follow the reviewed OLM boundaries, with expressly retained older forms where chosen.

In the reading text, capital letters remain unaccented: `Itaque`, `Angelus`, `Alii`. Supply stress accents on lowercase letters where needed, retaining the existing capitalization.

Predictable two-syllable words do not need stress accents; the reviewed forms include `neque`, `tempus`, `quinque`, and `illum`.

For an accented œ that Minion Pro cannot supply as a single glyph, use `oé`, as in `oboédiens`. Keep `oe` together under one GABC note group: `ob(h)oé(h)di(h)ens(h)`.

## Website

[index.md](index.md) is the catalogue used by GitHub Pages. Its layout and date-column controls are maintained separately in `_layouts/catalogue.html` and `assets/`. Calendar dates are retained from the existing catalogue; they are not computed by the website. Some sections list fewer years than others.

Each celebration has its own Markdown table, with cycle years A, B and C together. Short forms stay in the reading cells. Gospel settings share one reference and Textus button, with separate PDF links for the two tones. The Easter Vigil lists its seven Old Testament readings and epistle in a common table, followed by the Gospel cycles and their dates. Date columns without an existing entry show a dash; they do not imply that a date has been calculated.

The checked-in `assets/data/textus.json` supplies the Textus reader. The maintainer's local `tools/build_textus.py` regenerates it using the approved scores for reading selection and wording. That helper and the Notes export are deliberately not part of the repository. Matching Notes paragraphs supply paragraph boundaries when the alignment is sufficient. Source line wraps are joined; TeX double-quote pairs become typographic quotation marks for the website. Working annotations and out-of-pericope passages in Notes are not copied into the reading text.
