#!/bin/bash

# Initialize conda for shell script
source ~/anaconda3/etc/profile.d/conda.sh
conda activate STEER


cd /Users/nsiemons/Drive/Code_projects/STEER/steer-opencell-data/

echo "Migrating materials to AWS database..."
python -m steer_opencell_data.cli.migrate_record --table all --section materials --yes

echo "Migrating cells to AWS database..."
python -m steer_opencell_data.cli.migrate_record --table all --section cells --yes

echo "Database refresh complete."


