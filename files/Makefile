# LaTeX engine and flags
LATEXMK = latexmk -pdf -pdflatex=lualatex

# Find all .tex files under PA/ and SA/
TEXSRC := $(shell find PA SA -type f -name "*.tex")

# Convert to corresponding PDF targets
PDFS := $(TEXSRC:.tex=.pdf)

# Default: build all PDFs
all: $(PDFS)

# Rule: compile each .tex to .pdf in place
%.pdf: %.tex
	cd $(dir $<) && $(LATEXMK) $(notdir $<)

# Watch: recompile any .tex when changed
watch:
	@for f in $(TEXSRC); do \
	  echo "Watching $$f ..."; \
	  (cd $$(dirname $$f) && $(LATEXMK) -pvc $$(basename $$f)) & \
	done; \
	wait

# Clean auxiliary files across directories
clean:
	@for d in PA SA; do \
	  latexmk -C -cd -quiet -silent -outdir=$$d $$d/*.tex; \
	done

# Remove PDFs as well
distclean: clean
	@rm -f $(PDFS)

.PHONY: all watch clean distclean
