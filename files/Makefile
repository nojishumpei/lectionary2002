# Run from the repository root: make -C files -j10
# Build one reading:          make -C files AD/a01ep.pdf
# Requires LuaLaTeX, GregorioTeX (with autocompile), latexmk, and Minion Pro.
# Compatible with GNU Make 3.81 supplied by macOS.

.DEFAULT_GOAL := all

LATEXMK ?= latexmk
LATEXMKFLAGS ?= -lualatex -recorder -interaction=nonstopmode -halt-on-error -file-line-error

READING_DIRS := AD CH LT EA OT SA DE VO
TEX_SOURCES := $(sort $(foreach dir,$(READING_DIRS),$(wildcard $(dir)/*.tex)))
PDFS := $(TEX_SOURCES:.tex=.pdf)

# Count the selected PDFs before starting any parallel compilation jobs.
BUILD_GOALS := $(patsubst ./%,%,$(MAKECMDGOALS))
SELECTED_PDFS := $(filter $(PDFS),$(BUILD_GOALS))
COUNT_PDFS := $(if $(filter all count,$(BUILD_GOALS)),$(PDFS),$(if $(SELECTED_PDFS),$(SELECTED_PDFS),$(PDFS)))
COUNT_FORCE_OPTIONS := $(filter -g -gg -gt -g- --g --gg --gt --g-,$(LATEXMKFLAGS))
COUNT_FORCE := $(if $(filter -g -gg -gt --g --gg --gt,$(lastword $(COUNT_FORCE_OPTIONS))),--force)

.PHONY: all rebuild clean help count build-count check-tools FORCE

all: $(PDFS)

# Always let latexmk check its recorded inputs, including common/*.tex.
# Without FORCE, Make could skip latexmk when only a shared input changed.
# An unchanged document is checked without running LuaLaTeX. Each reading
# has its own auxiliary files, so separate readings can build in parallel.
$(PDFS): %.pdf: %.tex FORCE | build-count
	$(LATEXMK) $(LATEXMKFLAGS) -cd "$<"

# Preview the same estimate without compiling or changing auxiliary files.
count: build-count

build-count: | check-tools
	@perl build-count.pl $(COUNT_FORCE) $(COUNT_PDFS)

FORCE:

check-tools:
	@command -v "$(LATEXMK)" >/dev/null 2>&1 || { echo "latexmk not found; install it with your TeX distribution." >&2; exit 1; }
	@command -v lualatex >/dev/null 2>&1 || { echo "lualatex not found; install LuaLaTeX with your TeX distribution." >&2; exit 1; }

# Force a fresh LaTeX run for every reading; inherit the parent's -j limit.
# Do not run rebuild and all as simultaneous command-line goals.
rebuild:
	+$(MAKE) LATEXMKFLAGS="$(LATEXMKFLAGS) -g" all

# Remove disposable build records only. Preserve PDFs, TeX sources, and
# Gregorio's generated chant files. The next build recreates the records.
clean:
	find $(READING_DIRS) -type f \( -name '*.aux' -o -name '*.gaux' -o -name '*.log' -o -name '*.fls' -o -name '*.fdb_latexmk' -o -name '*.gsnippet' \) -exec rm -f {} +

help:
	@printf '%s\n' \
	  'make -C files -j10                 Check/build all $(words $(TEX_SOURCES)) readings, up to ten at once.' \
	  'make -C files AD/a01ep.pdf         Check/build one reading and its shared inputs.' \
	  'make -C files count                Estimate how many PDFs need rebuilding; do not compile.' \
	  'make -C files -j10 rebuild         Force compilation of all readings.' \
	  'make -C files clean                Remove auxiliary records; preserve PDFs.' \
	  'Run clean separately from builds. Build errors return a nonzero exit status.'
