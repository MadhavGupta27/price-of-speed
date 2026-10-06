# One-off: install R packages into the user library (system library is often read-only).
lib <- Sys.getenv("R_LIBS_USER")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
options(repos = "https://cloud.r-project.org")
install.packages(c("bibliometrix", "writexl", "readxl", "yaml"), lib = lib)
# Interactive GUI (Step 13): library(bibliometrix); biblioshiny()
