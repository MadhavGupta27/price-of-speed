# Bibliometric analyses and figures for the paper (PLAN.md Phase 3).
# Reads the cleaned sheet (records_with_gs.xlsx if present, else the raw export).
#
#   Rscript biblio/R/02_analysis.R
#
# Outputs figures to biblio/figures/ and tables to results/.

.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressMessages({ library(bibliometrix); library(ggplot2) })

src <- if (file.exists("biblio/exports/records_with_gs.xlsx")) "biblio/exports/records_with_gs.xlsx" else
       "biblio/exports/biblioshiny_export.xlsx"
message("Using ", src)
M <- as.data.frame(readxl::read_excel(src))
M[] <- lapply(M, function(x) if (is.character(x)) x else x)
M$PY <- as.integer(M$PY)
if ("GS_TC" %in% names(M)) M$TC <- as.numeric(M$GS_TC)  # Google Scholar counts drive "most cited"
M$TC[is.na(M$TC)] <- 0
class(M) <- c("bibliometrixDB", "data.frame")

fig <- function(name) file.path("biblio/figures", name)
dir.create("biblio/figures", showWarnings = FALSE)
dir.create("results", showWarnings = FALSE)
save_plot <- function(p, name, w = 7, h = 4.5) ggsave(fig(name), p, width = w, height = h, dpi = 300)
step <- function(label, expr) tryCatch(expr, error = function(e)
  message("SKIPPED ", label, ": ", conditionMessage(e)))

theme_paper <- theme_minimal(base_size = 11)
top_bar <- function(tab, n, xlab, name) {
  df <- head(data.frame(item = names(tab), n = as.numeric(tab)), n)
  df$item <- factor(df$item, levels = rev(df$item))
  save_plot(ggplot(df, aes(item, n)) + geom_col(fill = "#3b6ea5") + coord_flip() +
              labs(x = NULL, y = xlab) + theme_paper, name)
  write.csv(df, file.path("results", sub("\\.png$", ".csv", name)), row.names = FALSE)
}

res <- biblioAnalysis(M, sep = ";")
step("summary", capture.output(summary(res, k = 10, pause = FALSE), file = "results/biblio_summary.txt"))

step("annual production", {
  yr <- as.data.frame(table(M$PY)); names(yr) <- c("year", "n")
  yr$year <- as.integer(as.character(yr$year))
  write.csv(yr, "results/annual_production.csv", row.names = FALSE)
  save_plot(ggplot(yr, aes(year, n)) + geom_line(colour = "#3b6ea5") + geom_point() +
              labs(x = "Year", y = "Articles") + theme_paper, "annual_production.png")
})
step("top sources",  top_bar(res$Sources, 10, "Articles", "top_sources.png"))
step("top authors",  top_bar(res$Authors, 10, "Articles", "top_authors.png"))
step("top keywords", top_bar(res$DE, 20, "Occurrences", "top_keywords.png"))
step("countries",    top_bar(res$Countries, 10, "Articles", "top_countries.png"))

step("most cited", {
  mc <- M[order(-M$TC), intersect(c("TI", "AU", "PY", "SO", "DI", "TC"), names(M))]
  write.csv(head(mc, 25), "results/most_cited.csv", row.names = FALSE)
})

step("keyword co-occurrence", {
  NetMatrix <- biblioNetwork(M, analysis = "co-occurrences", network = "author_keywords", sep = ";")
  png(fig("keyword_cooccurrence.png"), width = 2400, height = 2000, res = 300)
  networkPlot(NetMatrix, n = 40, type = "fruchterman", Title = "", labelsize = 0.8,
              size.cex = TRUE, cluster = "louvain", remove.isolates = TRUE, verbose = TRUE)
  dev.off()
})

step("collaboration", {
  NetMatrix <- biblioNetwork(M, analysis = "collaboration", network = "authors", sep = ";")
  png(fig("author_collaboration.png"), width = 2400, height = 2000, res = 300)
  networkPlot(NetMatrix, n = 40, type = "fruchterman", Title = "", labelsize = 0.7,
              remove.isolates = TRUE, verbose = TRUE)
  dev.off()
})

step("thematic map", {
  tm <- thematicMap(M, field = "DE", n = 250, minfreq = 2, n.labels = 3)
  save_plot(tm$map, "thematic_map.png", 8, 6)
})

message("Done. Figures in biblio/figures/, tables in results/. Skipped steps need richer metadata.")
