#!/bin/bash

script_dir=$(dirname "$0")

python3 "$script_dir/arguments.py" > "$script_dir/app.default.conf"
