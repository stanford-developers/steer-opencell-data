#!/bin/bash
set -e  # Exit on any error

# Initialize conda for shell script
if [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
    conda activate STEER
else
    echo "ERROR: Conda not found at ~/anaconda3/etc/profile.d/conda.sh"
    exit 1
fi

# Set required environment variables for steer_opencell_design
export OPENCELL_ENV="development"
export API_URL="${API_URL:-http://localhost:8000}"  # Use provided API_URL or default to localhost

# Check if API is accessible (optional but helpful)
if ! curl -s -f -o /dev/null "$API_URL/health" 2>/dev/null; then
    echo "WARNING: Cannot connect to API at $API_URL"
    echo "Make sure the OpenCell API server is running or set API_URL environment variable"
    echo "Example: export API_URL=https://api.opencell.example.com/production"
fi

echo "Processing default_materials..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/default_materials/
for notebook in *.ipynb; do
    echo "  Executing: $notebook"
    if ! jupyter nbconvert --to notebook --execute --inplace "$notebook"; then
        echo "  ✗ Failed to execute $notebook"
        exit 1
    fi
done
echo "✓ Executed default_materials notebooks"
if jupyter nbconvert --clear-output --inplace *.ipynb; then
    echo "✓ Cleared default_materials outputs"
else
    echo "✗ Failed to clear outputs"
    exit 1
fi

echo "Processing cell_teardowns..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/cell_teardowns/
for notebook in *.ipynb; do
    echo "  Executing: $notebook"
    if ! jupyter nbconvert --to notebook --execute --inplace "$notebook"; then
        echo "  ✗ Failed to execute $notebook"
        exit 1
    fi
done
echo "✓ Executed cell_teardowns notebooks"
if jupyter nbconvert --clear-output --inplace *.ipynb; then
    echo "✓ Cleared cell_teardowns outputs"
else
    echo "✗ Failed to clear outputs"
    exit 1
fi

echo "Processing cell_references..."
cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/cell_references/
for notebook in *.ipynb; do
    # Skip temp.ipynb
    if [[ "$notebook" == "temp.ipynb" ]]; then
        echo "  Skipping: $notebook"
        continue
    fi
    echo "  Executing: $notebook"
    if ! jupyter nbconvert --to notebook --execute --inplace "$notebook"; then
        echo "  ✗ Failed to execute $notebook"
        exit 1
    fi
done
echo "✓ Executed cell_references notebooks"
if jupyter nbconvert --clear-output --inplace *.ipynb; then
    echo "✓ Cleared cell_references outputs"
else
    echo "✗ Failed to clear outputs"
    exit 1
fi

echo ""
echo "========================================="
echo "✓ All notebooks processed successfully!"
echo "========================================="
