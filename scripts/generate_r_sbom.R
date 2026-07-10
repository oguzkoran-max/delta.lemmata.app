args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
  stop("usage: generate_r_sbom.R OUTPUT_PATH")
}

source("renv/activate.R")

lock <- jsonlite::read_json("renv.lock", simplifyVector = FALSE)
version <- trimws(readLines("VERSION", warn = FALSE, n = 1L))
package_names <- sort(names(lock$Packages))

components <- lapply(package_names, function(package_name) {
  package <- lock$Packages[[package_name]]
  component <- list(
    type = "library",
    name = package_name,
    version = package$Version,
    purl = sprintf("pkg:cran/%s@%s", package_name, package$Version)
  )
  if (!is.null(package$License)) {
    component$licenses <- list(list(license = list(name = package$License)))
  }
  component
})

bom <- list(
  bomFormat = "CycloneDX",
  specVersion = "1.6",
  version = 1L,
  metadata = list(
    component = list(
      type = "application",
      name = "delta-lemmata",
      version = version
    )
  ),
  components = components
)

jsonlite::write_json(
  bom,
  path = args[[1L]],
  auto_unbox = TRUE,
  pretty = TRUE,
  null = "null"
)
cat(sprintf("r-sbom-ok components=%d\n", length(components)))
