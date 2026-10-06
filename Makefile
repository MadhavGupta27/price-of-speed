# Pipeline entry points. Python package lives in src/; PYTHONPATH is set
# explicitly because macOS can flag venv .pth files hidden, which Python 3.13 skips.
export PYTHONPATH := src
PY := uv run python
FAMILY ?= $(shell grep 'model_family:' config/project.yaml | awk '{print $$2}')
CROSSREF := $(if $(shell command -v pandoc-crossref),--filter pandoc-crossref,)
REFDOC := $(if $(wildcard paper/template.docx),--reference-doc template.docx,)

.PHONY: data case experiments setup test search-string biblio-import biblio-analysis prisma citations toy sensitivity paper todo

setup:            ## install Python + R dependencies
	uv sync --extra dev
	Rscript biblio/R/00_install.R

test:             ## run model/pipeline tests
	uv run pytest -q

search-string:    ## print the Boolean search string from config
	@$(PY) -c "from orpaper.config import load_config, search_string; print(search_string(load_config()))"

biblio-import:    ## Mendeley .bib -> bibliometrix -> biblio/exports/biblioshiny_export.xlsx
	Rscript biblio/R/01_import.R

biblio-analysis:  ## figures in biblio/figures, tables in results/
	Rscript biblio/R/02_analysis.R

prisma:           ## screening log -> PRISMA counts + flow diagram
	$(PY) scripts/prisma.py

citations:        ## make citations RETRIEVED=YYYY-MM-DD (needs Publish or Perish CSV)
	$(PY) scripts/merge_citations.py --retrieved $(RETRIEVED)

data:             ## fetch raw inputs (provenance -> data/raw/MANIFEST.json), audit Kaggle, build instance
	$(PY) scripts/fetch_data.py
	$(PY) scripts/audit_kaggle.py
	$(PY) scripts/build_instance.py

case:             ## E1 price-of-speed sweep on the Bengaluru instance
	$(PY) experiments/run_case.py

toy:              ## make toy [FAMILY=vrp]
	$(PY) experiments/run_toy.py --family $(FAMILY)

sensitivity:      ## make sensitivity [FAMILY=vrp]
	$(PY) experiments/run_sensitivity.py --family $(FAMILY)

experiments:      ## all paper experiments (E1 design, grid, PERT, assignment, transport, tornado)
	$(PY) experiments/run_design.py

paper:            ## export numbers/tables from results/, then compile paper/main.tex -> paper/build/main.pdf
	$(PY) scripts/export_numbers.py
	mkdir -p paper/build
	cd paper && tectonic -X compile main.tex --outdir build

todo:             ## list every outstanding human input
	@grep -rn "TODO(human)" --include=*.md --include=*.yaml --include=*.py --include=*.R --include=*.tex . \
	  | grep -v -e "^./.venv" -e "^./PLAN.md" -e "^./CLAUDE.md" -e "^./README.md"
