#!/usr/bin/env bash

if [ $# -ne 1 ] || [ $1 = "--help" ] || [ $1 = "-h" ]; then
    echo "usage: $0 RVM_ENV_DIR [--help]"
    echo "    RVM_ENV_DIR - Directory to create rvm environment in"
    exit 1
fi


# Get the rvm installer.  This is a known version that works reasonably well
RVM_INSTALLER=https://raw.github.com/wayneeseguin/rvm/d80282de1f2b2b1ff51740e05d9f5d84ebf3209f/binscripts/rvm-installer

env_dir=$1
mkdir "$env_dir" || exit 1
full_env_dir=`pwd`"/$env_dir"


\curl -L "$RVM_INSTALLER" | HOME=$full_env_dir bash -s -- stable --user-install --ignore-dotfiles || exit 1
bash -c '. '"$env_dir"'/.rvm/scripts/rvm && rvm install ruby' || exit 1
