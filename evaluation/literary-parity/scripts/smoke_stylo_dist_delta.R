#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
  stop("usage: smoke_stylo_dist_delta.R /path/to/stylo-package")
}

package_dir <- normalizePath(args[[1]], mustWork = TRUE)
description_path <- file.path(package_dir, "DESCRIPTION")
database_base <- file.path(package_dir, "R", "stylo")

if (!file.exists(description_path)) {
  stop("stylo DESCRIPTION is missing")
}
if (!file.exists(paste0(database_base, ".rdb")) ||
    !file.exists(paste0(database_base, ".rdx"))) {
  stop("stylo lazy-load database is incomplete")
}

description <- read.dcf(description_path)
version <- unname(description[1, "Version"])
built <- unname(description[1, "Built"])
if (!identical(version, "0.7.71")) {
  stop(sprintf("expected stylo 0.7.71, found %s", version))
}
if (!grepl("R 4\\.5\\.2", built)) {
  stop(sprintf("expected a package built with R 4.5.2, found %s", built))
}

# Load the exact package object database without attaching its optional GUI stack.
# This isolates the numerical Delta kernel from the macOS XQuartz dependency.
objects <- new.env(parent = globalenv())
invisible(lazyLoad(database_base, objects))
if (!exists("dist.delta", envir = objects, inherits = FALSE)) {
  stop("dist.delta is absent from the exact stylo object database")
}

dist_delta <- get("dist.delta", envir = objects, inherits = FALSE)
if (!identical(names(formals(dist_delta)), c("x", "scale"))) {
  stop("dist.delta formal arguments changed")
}

z_scores <- matrix(
  c(
    -1.0, 0.0, 1.0,
    -0.5, 1.0, -0.5,
    1.0, -1.0, 0.0
  ),
  nrow = 3L,
  byrow = TRUE,
  dimnames = list(c("doc-a", "doc-b", "doc-c"), c("f1", "f2", "f3"))
)

observed <- dist_delta(z_scores, scale = FALSE)
expected <- stats::dist(z_scores, method = "manhattan") / ncol(z_scores)
max_abs_difference <- max(abs(as.vector(observed) - as.vector(expected)))

if (!identical(attr(observed, "Labels"), rownames(z_scores))) {
  stop("dist.delta did not preserve ordered document labels")
}
if (!is.finite(max_abs_difference) || max_abs_difference > 1e-12) {
  stop(sprintf("dist.delta smoke comparison failed: %.17g", max_abs_difference))
}

cat(sprintf("r_version=%s\n", paste(R.version$major, R.version$minor, sep = ".")))
cat(sprintf("stylo_version=%s\n", version))
cat(sprintf("stylo_built=%s\n", built))
cat("loading_mode=exact_lazy_database_without_gui_namespace\n")
cat(sprintf("dist_delta_formals=%s\n", paste(names(formals(dist_delta)), collapse = ",")))
cat(sprintf("max_abs_difference=%.17g\n", max_abs_difference))
cat("smoke_test=pass\n")
