#!/bin/bash

# Array of folder names
folders=("folder1" "folder2" "folder3" "folder4")

# Loop through the array and create folders with pyvenv.cfg inside
for folder in "${folders[@]}"; do
    mkdir -p "./$folder"
    cp -r .venv "./$folder/"
done
