#!/usr/bin/env Rscript

fail <- function(code) {
  stop(code, call. = FALSE)
}

require_exact_names <- function(value, expected) {
  if (!is.list(value) || !identical(sort(names(value)), sort(expected))) {
    fail("ORACLE_INVALID_STRUCTURE")
  }
}

scalar_character <- function(value) {
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    fail("ORACLE_INVALID_SCALAR")
  }
  value
}

scalar_integer <- function(value) {
  if (!is.numeric(value) || length(value) != 1L || is.na(value) ||
      !is.finite(value) || value != floor(value)) {
    fail("ORACLE_INVALID_INTEGER")
  }
  as.integer(value)
}

array_character <- function(value) {
  if (!is.list(value) || length(value) < 1L) {
    fail("ORACLE_INVALID_ARRAY")
  }
  unname(vapply(value, scalar_character, character(1)))
}

array_integer <- function(value) {
  if (!is.list(value) || length(value) < 1L) {
    fail("ORACLE_INVALID_ARRAY")
  }
  unname(vapply(value, scalar_integer, integer(1)))
}

json_array <- function(value) {
  unname(as.list(value))
}

sort_json_objects <- function(value) {
  if (!is.list(value)) {
    return(value)
  }
  if (!is.null(names(value))) {
    value <- value[order(names(value), method = "radix")]
  }
  lapply(value, sort_json_objects)
}

encode_json <- function(value) {
  paste0(
    jsonlite::toJSON(
      sort_json_objects(value),
      auto_unbox = TRUE,
      digits = NA,
      null = "null",
      na = "null",
      pretty = FALSE
    ),
    "\n"
  )
}

write_atomic <- function(path, value) {
  temporary <- paste0(path, ".tmp")
  if (file.exists(temporary)) {
    unlink(temporary)
  }
  connection <- file(temporary, open = "wb")
  on.exit(close(connection), add = TRUE)
  writeBin(charToRaw(encode_json(value)), connection)
  close(connection)
  on.exit(NULL, add = FALSE)
  # These files contain only CC0 synthetic reference results and are committed
  # as public evidence.  Keep them readable by the host-side verifier even
  # when the container and CI runner use different unprivileged user IDs.
  Sys.chmod(temporary, mode = "0644")
  if (!file.rename(temporary, path)) {
    fail("ORACLE_WRITE_FAILED")
  }
}

read_json <- function(path) {
  info <- file.info(path)
  if (is.na(info$size) || !identical(info$isdir, FALSE) || info$size < 1 || info$size > 33554432) {
    fail("ORACLE_INPUT_FILE_INVALID")
  }
  text <- readChar(path, nchars = info$size, useBytes = TRUE)
  tryCatch(
    jsonlite::fromJSON(text, simplifyVector = FALSE),
    error = function(...) fail("ORACLE_JSON_INVALID")
  )
}

assert_environment <- function() {
  if (as.character(getRversion()) != "4.5.2") {
    fail("ORACLE_R_VERSION_INVALID")
  }
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    fail("ORACLE_JSONLITE_NAMESPACE_INVALID")
  }
  if (!requireNamespace("stylo", quietly = TRUE)) {
    fail("ORACLE_STYLO_NAMESPACE_INVALID")
  }
  if (as.character(utils::packageVersion("jsonlite")) != "2.0.0" ||
      as.character(utils::packageVersion("stylo")) != "0.7.71") {
    fail("ORACLE_PACKAGE_VERSION_INVALID")
  }
  if (Sys.getenv("LANG") != "C.UTF-8" ||
      Sys.getlocale("LC_COLLATE") != "C.UTF-8" ||
      Sys.getlocale("LC_CTYPE") != "C.UTF-8" ||
      Sys.getlocale("LC_NUMERIC") != "C" ||
      Sys.getenv("TZ") != "UTC") {
    fail("ORACLE_LOCALE_INVALID")
  }
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(20260713)
}

session_record <- function() {
  session <- utils::sessionInfo()
  kinds <- RNGkind()
  blas <- basename(scalar_character(session$BLAS))
  lapack <- basename(scalar_character(session$LAPACK))
  list(
    r_version = as.character(getRversion()),
    stylo_version = as.character(utils::packageVersion("stylo")),
    jsonlite_version = as.character(utils::packageVersion("jsonlite")),
    platform = R.version$platform,
    operating_system = R.version$os,
    lang = Sys.getenv("LANG"),
    lc_collate = Sys.getlocale("LC_COLLATE"),
    lc_ctype = Sys.getlocale("LC_CTYPE"),
    lc_numeric = Sys.getlocale("LC_NUMERIC"),
    timezone = Sys.getenv("TZ"),
    unicode_normalization = "NFC",
    rng_generator = kinds[[1]],
    rng_normal_generator = kinds[[2]],
    rng_sample_kind = kinds[[3]],
    seed = 20260713L,
    blas = blas,
    lapack = lapack
  )
}

utf8_key <- function(value) {
  paste(sprintf("%02x", as.integer(charToRaw(enc2utf8(value)))), collapse = "")
}

validate_request <- function(request) {
  require_exact_names(
    request,
    c(
      "analysis_unit", "candidate_features", "cells", "documents", "fits",
      "limit_profile", "request_id", "schema_version", "seed"
    )
  )
  if (scalar_character(request$schema_version) != "stylo-worker-input-v1" ||
      scalar_character(request$limit_profile) != "stylo-worker-contract-limits-v1" ||
      scalar_character(request$analysis_unit) != "whole_text" ||
      scalar_integer(request$seed) != 20260713L ||
      !grepl("^request_[0-9a-f]{64}$", scalar_character(request$request_id))) {
    fail("ORACLE_INPUT_CONTRACT_INVALID")
  }
  features <- array_character(request$candidate_features)
  if (length(features) > 20000L || anyDuplicated(features) ||
      any(nchar(features, type = "bytes") > 64L)) {
    fail("ORACLE_FEATURES_INVALID")
  }
  if (!is.list(request$documents) || length(request$documents) < 2L ||
      length(request$documents) > 50L) {
    fail("ORACLE_DOCUMENTS_INVALID")
  }
  documents <- lapply(request$documents, function(document) {
    require_exact_names(
      document,
      c("asset_ref", "counts", "document_id", "role", "token_total", "work_ref")
    )
    role <- scalar_character(document$role)
    counts <- array_integer(document$counts)
    token_total <- scalar_integer(document$token_total)
    if (!role %in% c("known", "unknown") || length(counts) != length(features) ||
        token_total < 1L || token_total > 3000000L || any(counts < 0L) ||
        any(counts > 3000000L) || sum(counts) > token_total ||
        !grepl("^doc_[0-9a-f]{64}$", scalar_character(document$document_id)) ||
        !grepl("^asset_[0-9a-f]{64}$", scalar_character(document$asset_ref)) ||
        !grepl("^work_[0-9a-f]{64}$", scalar_character(document$work_ref))) {
      fail("ORACLE_DOCUMENT_INVALID")
    }
    list(
      document_id = document$document_id,
      role = role,
      token_total = token_total,
      counts = counts
    )
  })
  document_ids <- vapply(documents, function(value) value$document_id, character(1))
  if (anyDuplicated(document_ids) ||
      sum(vapply(documents, function(value) value$role == "known", logical(1))) < 2L) {
    fail("ORACLE_DOCUMENT_GRAPH_INVALID")
  }
  if (!is.list(request$fits) || length(request$fits) < 1L || length(request$fits) > 64L) {
    fail("ORACLE_FITS_INVALID")
  }
  fits <- lapply(request$fits, function(fit) {
    require_exact_names(fit, c("culling_percent", "fit_id", "mfw"))
    mfw <- scalar_integer(fit$mfw)
    culling <- scalar_integer(fit$culling_percent)
    if (!grepl("^fit_[0-9a-f]{64}$", scalar_character(fit$fit_id)) ||
        mfw < 2L || mfw > 1000L || culling < 0L || culling > 100L) {
      fail("ORACLE_FIT_INVALID")
    }
    list(fit_id = fit$fit_id, mfw = mfw, culling_percent = culling)
  })
  fit_ids <- vapply(fits, function(value) value$fit_id, character(1))
  fit_keys <- vapply(
    fits,
    function(value) paste(value$mfw, value$culling_percent, sep = ":"),
    character(1)
  )
  if (anyDuplicated(fit_ids) || anyDuplicated(fit_keys) ||
      !is.list(request$cells) || length(request$cells) < 1L ||
      length(request$cells) > 192L) {
    fail("ORACLE_CELL_GRAPH_INVALID")
  }
  cells <- lapply(request$cells, function(cell) {
    require_exact_names(cell, c("cell_id", "distance", "fit_id"))
    distance <- scalar_character(cell$distance)
    if (!grepl("^cell_[0-9a-f]{64}$", scalar_character(cell$cell_id)) ||
        !scalar_character(cell$fit_id) %in% fit_ids ||
        !distance %in% c("classic_delta", "eders_delta", "cosine_delta")) {
      fail("ORACLE_CELL_INVALID")
    }
    list(cell_id = cell$cell_id, fit_id = cell$fit_id, distance = distance)
  })
  cell_ids <- vapply(cells, function(value) value$cell_id, character(1))
  cell_keys <- vapply(
    cells,
    function(value) paste(value$fit_id, value$distance, sep = ":"),
    character(1)
  )
  referenced <- unique(vapply(cells, function(value) value$fit_id, character(1)))
  if (anyDuplicated(cell_ids) || anyDuplicated(cell_keys) || !setequal(referenced, fit_ids)) {
    fail("ORACLE_CELL_GRAPH_INVALID")
  }
  list(
    request_id = request$request_id,
    features = features,
    documents = documents,
    fits = fits,
    cells = cells
  )
}

rank_features <- function(request) {
  known <- Filter(function(document) document$role == "known", request$documents)
  counts <- do.call(rbind, lapply(known, function(document) document$counts))
  totals <- colSums(counts)
  present <- colSums(counts > 0L)
  keep <- which(totals > 0)
  keys <- vapply(request$features[keep], utf8_key, character(1))
  ordered <- keep[order(-totals[keep], keys, method = "radix")]
  lapply(ordered, function(index) {
    list(
      feature = request$features[[index]],
      known_total_count = as.integer(totals[[index]]),
      known_document_count = as.integer(present[[index]])
    )
  })
}

fit_request <- function(request, ranked, fit) {
  known <- Filter(function(document) document$role == "known", request$documents)
  known_count <- length(known)
  eligible <- Filter(
    function(item) item$known_document_count * 100L >= fit$culling_percent * known_count,
    ranked
  )
  eligible_count <- length(eligible)
  if (eligible_count < fit$mfw) {
    return(list(
      result = list(
        fit_id = fit$fit_id,
        mfw = fit$mfw,
        culling_percent = fit$culling_percent,
        status = "not_enough_features",
        eligible_feature_count = eligible_count
      ),
      status = "not_enough_features"
    ))
  }
  selected <- vapply(eligible[seq_len(fit$mfw)], function(item) item$feature, character(1))
  indexes <- match(selected, request$features)
  frequencies <- do.call(
    rbind,
    lapply(
      request$documents,
      function(document) document$counts[indexes] * 100 / document$token_total
    )
  )
  known_rows <- vapply(request$documents, function(document) document$role == "known", logical(1))
  means <- colMeans(frequencies[known_rows, , drop = FALSE])
  deviations <- apply(frequencies[known_rows, , drop = FALSE], 2L, stats::sd)
  if (any(!is.finite(means)) || any(!is.finite(deviations)) || any(deviations <= 0)) {
    return(list(
      result = list(
        fit_id = fit$fit_id,
        mfw = fit$mfw,
        culling_percent = fit$culling_percent,
        status = "failed",
        eligible_feature_count = eligible_count,
        error_code = "non_positive_standard_deviation"
      ),
      status = "failed"
    ))
  }
  z_scores <- sweep(sweep(frequencies, 2L, means, "-"), 2L, deviations, "/")
  rownames(z_scores) <- vapply(request$documents, function(value) value$document_id, character(1))
  colnames(z_scores) <- selected
  list(
    result = list(
      fit_id = fit$fit_id,
      mfw = fit$mfw,
      culling_percent = fit$culling_percent,
      status = "complete",
      eligible_feature_count = eligible_count,
      selected_features = json_array(selected),
      means = json_array(as.numeric(means)),
      standard_deviations = json_array(as.numeric(deviations))
    ),
    status = "complete",
    z_scores = z_scores
  )
}

distance_matrix <- function(z_scores, distance) {
  result <- switch(
    distance,
    classic_delta = as.matrix(stylo::dist.delta(z_scores, scale = FALSE)),
    eders_delta = as.matrix(stylo::dist.eder(z_scores, scale = FALSE)),
    cosine_delta = as.matrix(stylo::dist.cosine(z_scores)),
    fail("ORACLE_DISTANCE_INVALID")
  )
  if (any(!is.finite(result)) || any(result < 0)) {
    fail("ORACLE_DISTANCE_FAILED")
  }
  result
}

analyze_request <- function(request) {
  ranked <- rank_features(request)
  fit_runs <- lapply(request$fits, function(fit) fit_request(request, ranked, fit))
  names(fit_runs) <- vapply(request$fits, function(fit) fit$fit_id, character(1))
  cells <- lapply(request$cells, function(cell) {
    fit_run <- fit_runs[[cell$fit_id]]
    if (fit_run$status == "not_enough_features") {
      return(list(
        cell_id = cell$cell_id,
        fit_id = cell$fit_id,
        distance = cell$distance,
        status = "not_enough_features",
        error_code = "not_enough_features"
      ))
    }
    if (fit_run$status == "failed") {
      return(list(
        cell_id = cell$cell_id,
        fit_id = cell$fit_id,
        distance = cell$distance,
        status = "failed",
        error_code = "fit_unavailable"
      ))
    }
    matrix <- tryCatch(
      distance_matrix(fit_run$z_scores, cell$distance),
      error = function(...) NULL
    )
    if (is.null(matrix)) {
      return(list(
        cell_id = cell$cell_id,
        fit_id = cell$fit_id,
        distance = cell$distance,
        status = "failed",
        error_code = "distance_calculation_failed"
      ))
    }
    list(
      cell_id = cell$cell_id,
      fit_id = cell$fit_id,
      distance = cell$distance,
      status = "complete",
      matrix = list(
        document_ids = json_array(rownames(matrix)),
        values = lapply(seq_len(nrow(matrix)), function(index) json_array(matrix[index, ]))
      )
    )
  })
  complete_count <- sum(vapply(cells, function(cell) cell$status == "complete", logical(1)))
  outcome <- if (complete_count == length(cells)) {
    "complete"
  } else if (complete_count > 0L) {
    "partial"
  } else {
    "failed"
  }
  list(
    outcome = outcome,
    fitting_basis = list(
      known_document_ids = json_array(vapply(
        Filter(function(document) document$role == "known", request$documents),
        function(document) document$document_id,
        character(1)
      )),
      ranked_features = lapply(ranked, identity)
    ),
    fits = unname(lapply(fit_runs, function(run) run$result)),
    cells = cells
  )
}

main <- function() {
  arguments <- commandArgs(trailingOnly = TRUE)
  if (length(arguments) != 2L) {
    fail("ORACLE_ARGUMENTS_INVALID")
  }
  manifest_path <- arguments[[1]]
  output_directory <- arguments[[2]]
  if (!dir.exists(output_directory)) {
    fail("ORACLE_OUTPUT_DIRECTORY_INVALID")
  }
  assert_environment()
  manifest <- read_json(manifest_path)
  require_exact_names(
    manifest,
    c(
      "description", "fixtures", "license", "license_file", "origin",
      "schema_version", "suite_id"
    )
  )
  suite_id <- scalar_character(manifest$suite_id)
  if (scalar_character(manifest$schema_version) != "p006-fixture-manifest-v1" ||
      !suite_id %in% c("p006-whole-text-v1", "p006-whole-text-v2") ||
      scalar_character(manifest$license) != "CC0-1.0" ||
      scalar_character(manifest$license_file) != "LICENSE" ||
      !is.list(manifest$fixtures) || length(manifest$fixtures) != 3L) {
    fail("ORACLE_MANIFEST_INVALID")
  }
  session <- session_record()
  input_directory <- dirname(manifest_path)
  output_names <- character()
  for (fixture in manifest$fixtures) {
    require_exact_names(
      fixture,
      c("expected_outcome", "fixture_ref", "input_file", "input_sha256", "purpose")
    )
    input_file <- scalar_character(fixture$input_file)
    if (!grepl("^[a-z0-9-]+\\.input\\.json$", input_file) ||
        !grepl("^fixture_[0-9a-f]{64}$", scalar_character(fixture$fixture_ref)) ||
        !grepl("^[0-9a-f]{64}$", scalar_character(fixture$input_sha256)) ||
        !scalar_character(fixture$expected_outcome) %in% c("complete", "partial")) {
      fail("ORACLE_MANIFEST_ENTRY_INVALID")
    }
    request <- validate_request(read_json(file.path(input_directory, input_file)))
    analysis <- analyze_request(request)
    if (analysis$outcome != fixture$expected_outcome) {
      fail("ORACLE_OUTCOME_MISMATCH")
    }
    output <- list(
      schema_version = "direct-stylo-oracle-v1",
      fixture_ref = fixture$fixture_ref,
      input_sha256 = fixture$input_sha256,
      request_id = request$request_id,
      limit_profile = "stylo-worker-contract-limits-v1",
      analysis_unit = "whole_text",
      seed = 20260713L,
      oracle_version = "p006-direct-stylo-v1",
      outcome = analysis$outcome,
      fitting_basis = analysis$fitting_basis,
      fits = analysis$fits,
      cells = analysis$cells,
      session = session
    )
    output_name <- sub("\\.input\\.json$", ".direct.json", input_file)
    output_names <- c(output_names, output_name)
    write_atomic(file.path(output_directory, output_name), output)
  }
  if (anyDuplicated(output_names)) {
    fail("ORACLE_OUTPUT_NAMES_INVALID")
  }
  write_atomic(file.path(output_directory, "session-info.json"), session)
}

tryCatch(main(), error = function(error) {
  message(conditionMessage(error))
  quit(save = "no", status = 1L, runLast = FALSE)
})
