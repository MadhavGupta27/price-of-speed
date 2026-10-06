# Step 13: load the Mendeley BibTeX export into bibliometrix and write the
# Excel sheet the group cleans by hand (Step 14).
#
#   Rscript biblio/R/01_import.R [path/to/library.bib]
#
# Outputs: biblio/exports/M_raw.rds, biblio/exports/biblioshiny_export.xlsx,
#          results/field_completeness.csv

.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressMessages({ library(bibliometrix); library(yaml) })

cfg <- yaml::read_yaml("config/project.yaml")
args <- commandArgs(trailingOnly = TRUE)
bib <- if (length(args)) args[[1]] else cfg$bibliometrix$bib_file
if (!file.exists(bib)) stop("BibTeX not found: ", bib, " - export it from Mendeley (Step 12).")

# Mendeley/EBSCO BibTeX is not a native bibliometrix source. Try the configured
# dbsource, then fall back to the other, and keep whichever keeps more fields.
try_import <- function(db) tryCatch(
  suppressWarnings(convert2df(bib, dbsource = db, format = "bibtex")),
  error = function(e) { message("dbsource=", db, " failed: ", conditionMessage(e)); NULL })

sources <- unique(c(cfg$bibliometrix$dbsource, "scopus", "generic"))
M <- NULL
for (db in sources) {
  M <- try_import(db)
  if (!is.null(M) && nrow(M) > 0) { message("Imported ", nrow(M), " records with dbsource=", db); break }
}
if (is.null(M) || nrow(M) == 0) stop("Import failed for all dbsources. See PLAN.md Phase 3 risk note.")

# Mendeley writes all keywords to `keywords`, which the scopus parser files under
# ID (Keywords Plus). Author keywords (DE) drive most analyses, so copy them over.
is_blank <- function(x) is.na(x) | trimws(as.character(x)) %in% c("", "NA", "none", "NONE")
if (all(is_blank(M$DE)) && "ID" %in% names(M) && !all(is_blank(M$ID))) {
  M$DE <- M$ID
  message("Copied Mendeley keywords (ID) into author keywords (DE).")
}

# Field completeness: which analyses the data can support. bibliometrix fills
# missing CR with "none" and TC with 0, so treat those placeholders as missing.
fields <- c(AU = "Authors", TI = "Title", SO = "Source", PY = "Year", DI = "DOI",
            DE = "Author keywords", ID = "Keywords Plus", AB = "Abstract",
            C1 = "Affiliations", CR = "Cited references", TC = "Times cited")
comp <- data.frame(
  tag = names(fields), field = unname(fields),
  present = sapply(names(fields), function(f)
    if (!f %in% names(M)) 0 else if (f == "TC") round(100 * mean(as.numeric(M$TC) > 0, na.rm = TRUE), 1)
    else round(100 * mean(!is_blank(M[[f]])), 1)))
dir.create("results", showWarnings = FALSE)
write.csv(comp, "results/field_completeness.csv", row.names = FALSE)
print(comp, row.names = FALSE)
if (comp$present[comp$tag == "CR"] < 50)
  message("NOTE: cited references mostly missing -> co-citation / historiograph analyses unavailable.")
if (comp$present[comp$tag == "TC"] < 50)
  message("NOTE: no citation counts -> add Google Scholar counts (scripts/merge_citations.py).")
if (comp$present[comp$tag == "DE"] < 50)
  message("NOTE: author keywords mostly missing -> fix in Mendeley metadata (Step 11) before analysis.")

dir.create("biblio/exports", showWarnings = FALSE)
saveRDS(M, "biblio/exports/M_raw.rds")
writexl::write_xlsx(M, "biblio/exports/biblioshiny_export.xlsx")
message("Wrote biblio/exports/biblioshiny_export.xlsx - clean it by hand, then add GS citations.")
