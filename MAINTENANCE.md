# Maintenance notes

Technical reference for transcribing, compiling, and maintaining the collection.

## Building individual scores

The scores require LuaLaTeX, GregorioTeX, latexmk, Make, and an installed copy of Minion Pro. The font is not included.

From the repository root, check and build all readings with up to ten concurrent jobs, or build a single reading:

```sh
make -C files -j10
make -C files AD/a01ep.pdf
```

The Makefile lets latexmk check each reading’s recorded inputs, including shared introductions and the preamble. Unchanged documents do not run LuaLaTeX. The first build in a fresh checkout establishes these records and may recompile existing PDFs. Keep the auxiliary records for incremental builds.

Before starting the parallel jobs, Make prints a rebuild estimate, for example `PDF rebuild estimate: 12 of 1113 (1101 up to date).` Run `make -C files count` to display the estimate without compiling or changing build records. For a single PDF target, the count covers that target alone.

The small Perl helper `files/build-count.pl` reads latexmk’s saved input checksums for the default LuaLaTeX workflow, so a timestamp change alone does not count as a rebuild. It also detects missing PDFs or auxiliary files and forced builds. Incomplete or unsupported records are reported separately as needing latexmk’s check. Latexmk makes the final compilation decisions; changes during the build or custom latexmk configuration can affect the result.

Use `make -C files -j10 rebuild` to force compilation of all readings. `make -C files clean` removes auxiliary records while preserving PDFs and sources; run cleanup separately from builds. For a direct manual build, run `lualatex a01ep.tex` from `files/AD`.

## Building book arrangements

Run these commands from the repository root.

```sh
python3 books/build.py --lectern -j 10
python3 books/build.py --pulpit -j 10
```

| Mode | Default PDF | Build directory |
| --- | --- | --- |
| Lectern book (`--lectern`, default) | `books/lectern.pdf` | `build/lectern/` |
| Gospel book (`--pulpit`) | `books/pulpit.pdf` | `build/pulpit/` |
| Lectern proof (`--lectern-sample`, alias `--sample`) | `books/lectern-sample.pdf` | `build/lectern-sample/` |
| Gospel proof (`--pulpit-sample`) | `books/pulpit-sample.pdf` | `build/pulpit-sample/` |

The builder requires Python 3.9 or later, LuaLaTeX, Gregorio/GregorioTeX, Minion Pro (including Semibold), and Helvetica Neue Bold for the year badges. Install the fonts separately. Both books compile directly from the canonical TeX sources and use `index.md` to establish reading order. An eligible source without a catalogue link is reported as an error.

The lectern book contains first and second readings, including optional readings and both long and short forms.

The Gospel book contains Gospel readings in Tonus Evangelii, Tonus ad libitum, and Tonus Antiquior.

The front table of contents is headed *Index generalis*. The *Index lectionum* at the back follows the Nova Vulgata's book order and links each Scripture reference to the start of its setting. The Gospel index gives a separate page number for each tone.

Each build directory holds the staged reading copies, logs, cached groups, and `build-report.json` with the reading selection, tool versions, and input and output hashes. The builder checks input and PDF hashes before reusing groups or the final assembly. It replaces the output only after the selected groups and the final assembly succeed. Git ignores the build directories and the two proof PDFs.

| Option | Purpose |
| --- | --- |
| `--list` | List the selected readings without compiling or writing files. |
| `--rebuild` | Recompile all selected groups and the final assembly. Use after changing installed fonts or TeX packages. |
| `--build-dir PATH` | Choose another directory for build files and the reusable cache. |
| `-o PATH`, `--output PATH` | Choose another output PDF. |
| `-j N`, `--jobs N` | Set the number of parallel TeX jobs; the default is up to ten. |

Both books load their shared page, grid, and chant settings from `books/layout/book-profile.tex`. Gospel-specific headings and dialogue spacing are in `books/layout/book-pulpit-heads.tex`. Maintain printed title breaks in `books/book_titles.py` and calendar calculations in `books/book_calendar.py` and `books/build.py`.

After changing readings or book layout, rebuild each affected volume. Review its table of contents, Scripture index, calendar tables, long and short form boundaries, and page breaks before committing the sources and updated PDFs together. Run the Python selection and reading-adapter checks with the following command.

```sh
python3 -m unittest discover -s books -p 'test_*.py'
```

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

`files/common/preamble.tex` controls the presentation. Use `\massdesignation{Ad Missam in Vigilia}` for a particular Mass, `\readingnumber{13}` for a sequential reading option (printed as `N. 13`), and `\readingnote{Ad Libitum}` for an additional qualification. These fields are independent of the year cycle. A shorter reading uses `\readingform{Forma Brevior}` even when no chant tone is specified. When a shorter form exists, its longer counterpart uses `\readingform{Forma Longior}`. Label both forms in the catalogue.

Scriptural references use the Latin book abbreviations from the *Ordo lectionum Missæ*.

## Website

[index.md](index.md) is the catalogue used by GitHub Pages. Its layout and date-column controls are maintained separately in `_layouts/catalogue.html` and `assets/`..

Each celebration has its own Markdown table, with cycle years A, B and C together. Short forms stay in the reading cells. Gospel settings share one reference and Textus button, with separate PDF links for Tonus Antiquior, Tonus Evangelii, and Tonus ad libitum. The Easter Vigil lists its seven Old Testament readings and epistle in a common table, followed by the Gospel cycles and their dates. Date columns without an existing entry show a dash; they do not imply that a date has been calculated.

The checked-in `assets/data/textus.json` supplies the Textus reader.
