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
pip install -U pytaxonomies
python3 app.py -tg


echo ""
echo "################"
echo "# MISP Modules #"
echo "################"
pip install -U misp-modules
python3 app.py -mm
