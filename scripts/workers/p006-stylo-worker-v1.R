#!/usr/bin/env Rscript

REQUEST_COMPONENT <- "28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"
RESULT_COMPONENT <- "053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"
FATAL_COMPONENT <- "24ae13b5ee15a59e2f7924a480c4160907d13e900a8d879f1d81b0faab8f6548"
RESULT_TEMP_COMPONENT <- "3d0d526ae03cedf6fb20176f11849aa6f4d04cb0d1737d57fe36e58b156dfae0"
FATAL_TEMP_COMPONENT <- "2ae6dc29c824605557cb70e37858793e34cf6df430099aef05cd3b17f025d65f"

fail <- function(code) {
  stop(code, call. = FALSE)
}

require_exact_names <- function(value, expected) {
  if (!is.list(value) || !identical(sort(names(value)), sort(expected))) {
    fail("WORKER_INVALID_STRUCTURE")
  }
}

scalar_character <- function(value) {
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    fail("WORKER_INVALID_SCALAR")
  }
  value
}

scalar_integer <- function(value) {
  if (!is.numeric(value) || length(value) != 1L || is.na(value) ||
      !is.finite(value) || value != floor(value)) {
    fail("WORKER_INVALID_INTEGER")
  }
  as.integer(value)
}

array_character <- function(value) {
  if (!is.list(value) || length(value) < 1L) {
    fail("WORKER_INVALID_ARRAY")
  }
  unname(vapply(value, scalar_character, character(1)))
}

array_integer <- function(value) {
  if (!is.list(value) || length(value) < 1L) {
    fail("WORKER_INVALID_ARRAY")
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

is_symlink <- function(path) {
  target <- Sys.readlink(path)
  !is.na(target) && nzchar(target)
}

write_atomic <- function(path, temporary, value) {
  if (file.exists(path) || file.exists(temporary) ||
      is_symlink(path) || is_symlink(temporary)) {
    fail("WORKER_OUTPUT_EXISTS")
  }
  connection <- file(temporary, open = "wb")
  closed <- FALSE
  on.exit({
    if (!closed) {
      close(connection)
    }
    if (file.exists(temporary)) {
      unlink(temporary)
    }
  }, add = TRUE)
  Sys.chmod(temporary, mode = "0600")
  writeBin(charToRaw(encode_json(value)), connection)
  close(connection)
  closed <- TRUE
  if (!file.rename(temporary, path)) {
    fail("WORKER_OUTPUT_RENAME_FAILED")
  }
  on.exit(NULL, add = FALSE)
}

emit_fatal <- function(stage, code, request_id = NULL) {
  payload <- list(
    schema_version = "stylo-worker-fatal-error-v1",
    request_id = request_id,
    worker_version = "stylo-worker-v1",
    status = "fatal_error",
    stage = stage,
    error_code = code
  )
  written <- tryCatch({
    write_atomic(FATAL_COMPONENT, FATAL_TEMP_COMPONENT, payload)
    TRUE
  }, error = function(...) FALSE)
  quit(save = "no", status = if (written) 0L else 1L, runLast = FALSE)
}

bootstrap_environment <- function() {
  arguments <- commandArgs(trailingOnly = FALSE)
  script_arguments <- arguments[startsWith(arguments, "--file=")]
  if (length(script_arguments) != 1L) {
    fail("WORKER_BOOTSTRAP_SCRIPT_INVALID")
  }
  script_path <- normalizePath(sub("^--file=", "", script_arguments[[1]]), mustWork = TRUE)
  project_root <- dirname(dirname(dirname(script_path)))
  activation <- file.path(project_root, "renv", "activate.R")
  if (!file.exists(activation) || is_symlink(activation)) {
    fail("WORKER_BOOTSTRAP_RENV_INVALID")
  }
  Sys.setenv(RENV_PROJECT = project_root)
  source(activation, local = .GlobalEnv)
}

read_request_text <- function() {
  if (!file.exists(REQUEST_COMPONENT) || is_symlink(REQUEST_COMPONENT)) {
    emit_fatal("input_read", "INPUT_MISSING")
  }
  info <- file.info(REQUEST_COMPONENT)
  if (is.na(info$size) || !identical(info$isdir, FALSE) ||
      info$size < 1 || info$size > 33554432) {
    emit_fatal("input_read", "INPUT_TOO_LARGE")
  }
  connection <- file(REQUEST_COMPONENT, open = "rb")
  on.exit(close(connection), add = TRUE)
  payload <- readBin(connection, what = "raw", n = info$size)
  if (length(payload) != info$size) {
    emit_fatal("input_read", "INPUT_MISSING")
  }
  text <- rawToChar(payload)
  if (!validUTF8(text)) {
    emit_fatal("input_parse", "INPUT_INVALID_UTF8")
  }
  text
}

assert_environment <- function() {
  if (as.character(getRversion()) != "4.5.2") {
    fail("WORKER_ENV_R_VERSION_INVALID")
  }
  if (!requireNamespace("jsonlite", quietly = TRUE) ||
      as.character(utils::packageVersion("jsonlite")) != "2.0.0") {
    fail("WORKER_ENV_JSONLITE_INVALID")
  }
  if (!requireNamespace("stylo", quietly = TRUE) ||
      as.character(utils::packageVersion("stylo")) != "0.7.71") {
    fail("WORKER_ENV_STYLO_INVALID")
  }
  if (Sys.getenv("LANG") != "C.UTF-8") {
    fail("WORKER_ENV_LANG_INVALID")
  }
  if (Sys.getlocale("LC_COLLATE") != "C.UTF-8") {
    fail("WORKER_ENV_COLLATE_INVALID")
  }
  if (Sys.getlocale("LC_CTYPE") != "C.UTF-8") {
    fail("WORKER_ENV_CTYPE_INVALID")
  }
  if (Sys.getlocale("LC_NUMERIC") != "C") {
    fail("WORKER_ENV_NUMERIC_INVALID")
  }
  if (Sys.getenv("TZ") != "UTC") {
    fail("WORKER_ENV_TIMEZONE_INVALID")
  }
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(20260713)
}

session_record <- function() {
  session <- utils::sessionInfo()
  kinds <- RNGkind()
  list(
    r_version = as.character(getRversion()),
    stylo_version = as.character(utils::packageVersion("stylo")),
    jsonlite_version = as.character(utils::packageVersion("jsonlite")),
    platform = scalar_character(R.version$platform),
    operating_system = scalar_character(R.version$os),
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
    blas = basename(scalar_character(session$BLAS)),
    lapack = basename(scalar_character(session$LAPACK))
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
  request_id <- scalar_character(request$request_id)
  if (scalar_character(request$schema_version) != "stylo-worker-input-v1" ||
      scalar_character(request$limit_profile) != "stylo-worker-contract-limits-v1" ||
      scalar_character(request$analysis_unit) != "whole_text" ||
      scalar_integer(request$seed) != 20260713L ||
      !grepl("^request_[0-9a-f]{64}$", request_id)) {
    fail("WORKER_INPUT_CONTRACT_INVALID")
  }
  features <- array_character(request$candidate_features)
  if (length(features) > 20000L || anyDuplicated(features) ||
      any(nchar(features, type = "bytes") > 64L)) {
    fail("WORKER_FEATURES_INVALID")
  }
  if (!is.list(request$documents) || length(request$documents) < 2L ||
      length(request$documents) > 50L) {
    fail("WORKER_DOCUMENTS_INVALID")
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
      fail("WORKER_DOCUMENT_INVALID")
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
    fail("WORKER_DOCUMENT_GRAPH_INVALID")
  }
  if (!is.list(request$fits) || length(request$fits) < 1L ||
      length(request$fits) > 64L) {
    fail("WORKER_FITS_INVALID")
  }
  fits <- lapply(request$fits, function(fit) {
    require_exact_names(fit, c("culling_percent", "fit_id", "mfw"))
    mfw <- scalar_integer(fit$mfw)
    culling <- scalar_integer(fit$culling_percent)
    if (!grepl("^fit_[0-9a-f]{64}$", scalar_character(fit$fit_id)) ||
        mfw < 2L || mfw > 1000L || culling < 0L || culling > 100L) {
      fail("WORKER_FIT_INVALID")
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
    fail("WORKER_CELL_GRAPH_INVALID")
  }
  cells <- lapply(request$cells, function(cell) {
    require_exact_names(cell, c("cell_id", "distance", "fit_id"))
    distance <- scalar_character(cell$distance)
    fit_id <- scalar_character(cell$fit_id)
    if (!grepl("^cell_[0-9a-f]{64}$", scalar_character(cell$cell_id)) ||
        !fit_id %in% fit_ids ||
        !distance %in% c("classic_delta", "eders_delta", "cosine_delta")) {
      fail("WORKER_CELL_INVALID")
    }
    list(cell_id = cell$cell_id, fit_id = fit_id, distance = distance)
  })
  cell_ids <- vapply(cells, function(value) value$cell_id, character(1))
  cell_keys <- vapply(
    cells,
    function(value) paste(value$fit_id, value$distance, sep = ":"),
    character(1)
  )
  referenced <- unique(vapply(cells, function(value) value$fit_id, character(1)))
  if (anyDuplicated(cell_ids) || anyDuplicated(cell_keys) ||
      !setequal(referenced, fit_ids)) {
    fail("WORKER_CELL_GRAPH_INVALID")
  }
  list(
    request_id = request_id,
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
    fail("WORKER_DISTANCE_INVALID")
  )
  if (any(!is.finite(result)) || any(result < 0)) {
    fail("WORKER_DISTANCE_FAILED")
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
  Sys.umask("0077")
  if (length(commandArgs(trailingOnly = TRUE)) != 0L) {
    fail("WORKER_ARGUMENTS_INVALID")
  }
  bootstrap_environment()
  text <- read_request_text()
  decoded <- tryCatch(
    jsonlite::fromJSON(text, simplifyVector = FALSE),
    error = function(...) NULL
  )
  if (is.null(decoded)) {
    emit_fatal("input_parse", "INPUT_INVALID_JSON")
  }
  request <- tryCatch(validate_request(decoded), error = function(...) NULL)
  if (is.null(request)) {
    emit_fatal("input_validate", "INPUT_INVALID_CONTRACT")
  }
  environment_ready <- tryCatch({
    assert_environment()
    TRUE
  }, error = function(...) FALSE)
  if (!environment_ready) {
    emit_fatal("engine_init", "ENVIRONMENT_INVALID", request$request_id)
  }
  analysis <- tryCatch(analyze_request(request), error = function(...) NULL)
  if (is.null(analysis)) {
    emit_fatal("analysis", "ANALYSIS_FAILED", request$request_id)
  }
  output <- list(
    schema_version = "stylo-worker-result-v1",
    request_id = request$request_id,
    limit_profile = "stylo-worker-contract-limits-v1",
    analysis_unit = "whole_text",
    seed = 20260713L,
    worker_version = "stylo-worker-v1",
    outcome = analysis$outcome,
    fitting_basis = analysis$fitting_basis,
    fits = analysis$fits,
    cells = analysis$cells,
    session = session_record()
  )
  written <- tryCatch({
    write_atomic(RESULT_COMPONENT, RESULT_TEMP_COMPONENT, output)
    TRUE
  }, error = function(...) FALSE)
  if (!written) {
    emit_fatal("result_write", "RESULT_WRITE_FAILED", request$request_id)
  }
}

tryCatch(
  main(),
  error = function(...) quit(save = "no", status = 1L, runLast = FALSE)
)
