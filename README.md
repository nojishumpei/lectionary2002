# Lectionary2002

Latin readings for Mass according to the 2002 Roman Missal, pointed in Gregorian chant notation with GregorioTeX.

**[Browse the readings and download PDFs](https://nojishumpei.github.io/lectionary2002/)** · [Catalogue source](index.md)

The catalogue includes the temporal and sanctoral cycles, votive Masses, and Masses for the Dead. Gospel readings are provided in the Ancient and Gospel tones. The repository contains 880 reading PDFs and their TeX sources.

## Files

| Directory | Contents |
|:--|:--|
| `files/AD` | Advent |
| `files/CH` | Christmas season |
| `files/LT` | Lent |
| `files/EA` | Easter season |
| `files/OT` | Ordinary Time |
| `files/SA` | Saints and other celebrations |
| `files/DE` | Masses for the Dead |
| `files/VO` | Votive Masses |
| `files/common` | Shared preamble, introductions, and conclusions |

## Building the scores

The scores require LuaLaTeX, GregorioTeX, latexmk, Make, and an installed copy of Minion Pro. The font is not included.

From the repository root, check and build all readings with up to ten concurrent jobs, or build a single reading:

```sh
make -C files -j10
make -C files AD/a01ep.pdf
```

The Makefile lets latexmk check each reading’s recorded inputs, including shared introductions and the preamble. Unchanged documents do not run LuaLaTeX. The first build in a fresh checkout establishes these records and may recompile existing PDFs. Keep the auxiliary records for incremental builds.

Use `make -C files -j10 rebuild` to force compilation of all readings. `make -C files clean` removes auxiliary records while preserving PDFs and sources; run cleanup separately from builds. For a direct manual build, run `lualatex a01ep.tex` from `files/AD`.

The source commands distinguish a year cycle, such as `\yearcycle{Year A}`, from a sequential reading option, such as `\readingnumber{13}`.

## Website

[index.md](index.md) is the catalogue used by GitHub Pages. Its layout and date-column controls are maintained separately in `_layouts/catalogue.html` and `assets/`. Calendar dates are retained from the existing catalogue; they are not computed by the website. Some sections list fewer years than others.

Sources and related resources are listed at the end of the [catalogue](index.md#resources).
