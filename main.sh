#! /usr/bin/env bash

cwd=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

pushd $cwd
source venv/bin/activate
python3 main.py
