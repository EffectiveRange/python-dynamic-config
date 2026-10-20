#!/bin/bash

script_dir=$(dirname "$0")

python3 "$script_dir/app.py" --config-dir "$script_dir/config"
