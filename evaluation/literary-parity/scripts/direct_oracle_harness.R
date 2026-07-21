#!/usr/bin/env Rscript

# Execute the exact frozen P006 direct-stylo definitions for one literary request.

fail_harness <- function(code) {
  stop(code, call. = FALSE)
}

main_harness <- function() {
  arguments <- commandArgs(trailingOnly = TRUE)
  if (length(arguments) != 3L) {
    fail_harness("LITERARY_ORACLE_ARGUMENTS_INVALID")
  }
  request_path <- normalizePath(arguments[[1]], mustWork = TRUE)
  output_path <- arguments[[2]]
  input_sha256 <- arguments[[3]]
  if (!grepl("^[0-9a-f]{64}$", input_sha256)) {
    fail_harness("LITERARY_ORACLE_INPUT_SHA_INVALID")
  }

  setwd("/opt/delta")
  Sys.setenv(RENV_PROJECT = "/opt/delta")
  source("renv/activate.R", local = .GlobalEnv)

  frozen_source <- readLines(
    "/opt/delta/scripts/oracles/p006-direct-stylo-v1.R",
    warn = FALSE,
    encoding = "UTF-8"
  )
  boundary <- grep("^main <- function\\(\\) \\{$", frozen_source)
  if (length(boundary) != 1L || boundary[[1]] < 2L) {
    fail_harness("LITERARY_ORACLE_FROZEN_SOURCE_BOUNDARY_INVALID")
  }
  definitions <- paste(frozen_source[seq_len(boundary[[1]] - 1L)], collapse = "\n")
  eval(parse(text = definitions, keep.source = FALSE), envir = .GlobalEnv)

  assert_environment()
  decoded <- read_json(request_path)
  request <- validate_request(decoded)
  analysis <- analyze_request(request)
  if (analysis$outcome != "complete") {
    fail_harness("LITERARY_ORACLE_NONCOMPLETE_OUTCOME")
  }
  output <- list(
    schema_version = "direct-stylo-oracle-v1",
    fixture_ref = sub("^request_", "fixture_", request$request_id),
    input_sha256 = input_sha256,
    request_id = request$request_id,
    limit_profile = "stylo-worker-contract-limits-v1",
    analysis_unit = "whole_text",
    seed = 20260713L,
    oracle_version = "p006-direct-stylo-v1",
    outcome = analysis$outcome,
    fitting_basis = analysis$fitting_basis,
    fits = analysis$fits,
    cells = analysis$cells,
    session = session_record()
  )
  write_atomic(output_path, output)
  write_atomic(file.path(dirname(output_path), "direct-session-info.json"), output$session)
}

tryCatch(
  main_harness(),
  error = function(error) {
    message(conditionMessage(error))
    quit(save = "no", status = 1L, runLast = FALSE)
  }
)
