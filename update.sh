#!/bin/bash
set -e
source env/bin/activate

## Get update from git
echo "##########"
echo "Git pull"
echo "##########"
git pull

## Copy db for migration
echo ""
echo "##########"
echo "Migration"
echo "##########"
if [ ! -d "instance/backup" ]; then
  mkdir instance/backup
fi
cp instance/flowintel.sqlite instance/backup/$(date +"%Y_%m_%d").sqlite

## Run migration
./migrate.sh -u

echo ""
echo "##########"
echo "Submodule"
echo "Update"
echo "##########"
## Update submodules
git submodule update --remote
python3 app.py -tg
