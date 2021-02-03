#!/usr/bin/env bash
sudo apt install r-base
# create empty folder for user library.
# necessary for non-root users who have
# never installed an R package before.
# Alternatively, we require the renv
# package to be installed already, then we can
# omit that.
Rscript -e 'dir.create(Sys.getenv("R_LIBS_USER"), recursive = TRUE)'
