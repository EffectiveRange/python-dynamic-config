#!/bin/bash

script_dir=$(dirname "$0")
config_dir="$script_dir/config"
default_conf="$config_dir/app.default.conf"

rm -f "$default_conf"
mkdir -p "$config_dir"

printf "Generating default configuration at %s:\n\n" "$default_conf"

python3 "$script_dir/app_args.py" | tee "$default_conf"
