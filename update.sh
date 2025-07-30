#!/bin/bash
set -e
source env/bin/activate

./launch.sh -ks

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
pip install -U pytaxonomies pymispgalaxies pymisp
python3 app.py -tg
python3 app.py -py


echo ""
echo "################"
echo "# MISP Modules #"
echo "################"

pip install -U misp-modules

screen -dmS "misp_mod_flowintel"
screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"

python3 app.py -mm

./launch.sh -ks