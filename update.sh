#!/bin/bash
source env/bin/activate

## Get update from git
git pull

## Copy db for migration
if [ ! -d "instance/backup" ]; then
  mkdir instance/backup
fi
cp instance/flowintel.sqlite instance/backup/$(date +"%Y_%m_%d").sqlite

## Run migration
./migrate.sh -u

## Update submodules
git submodule update
python3 app.py -tg
