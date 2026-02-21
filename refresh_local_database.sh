#!/bin/bash

# Initialize conda for shell script
source ~/anaconda3/etc/profile.d/conda.sh
conda activate STEER

echo "Processing default_materials..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/default_materials/
for notebook in *.ipynb; do
    echo "  Executing: $notebook"
    jupyter nbconvert --to notebook --execute --inplace "$notebook" > /dev/null 2>&1
done
echo "✓ Executed default_materials notebooks"
jupyter nbconvert --clear-output --inplace *.ipynb > /dev/null 2>&1 && echo "✓ Cleared default_materials outputs"

echo "Processing cell_teardowns..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/cell_teardowns/
for notebook in *.ipynb; do
    echo "  Executing: $notebook"
    jupyter nbconvert --to notebook --execute --inplace "$notebook" > /dev/null 2>&1
done
echo "✓ Executed cell_teardowns notebooks"
jupyter nbconvert --clear-output --inplace *.ipynb > /dev/null 2>&1 && echo "✓ Cleared cell_teardowns outputs"

echo "Processing cell_references..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/cell_references/
for notebook in *.ipynb; do
    echo "  Executing: $notebook"
    jupyter nbconvert --to notebook --execute --inplace "$notebook" > /dev/null 2>&1
done
echo "✓ Executed cell_references notebooks"
jupyter nbconvert --clear-output --inplace *.ipynb > /dev/null 2>&1 && echo "✓ Cleared cell_references outputs"


