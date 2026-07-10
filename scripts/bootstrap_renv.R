required_r <- "4.5.2"
actual_r <- as.character(getRversion())
if (!identical(actual_r, required_r)) {
  stop(sprintf("R %s is required; found %s", required_r, actual_r))
}

if (!file.exists("renv/activate.R")) {
  stop("renv/activate.R is missing; P001 lock bootstrap is incomplete")
}

source("renv/activate.R")
renv::restore(prompt = FALSE)
renv::status()
cat("renv-restore-ok\n")
