#!/bin/bash

sudo apt-get update
sudo apt-get install python3-pip screen virtualenv

virtualenv env
source env/bin/activate
pip install -r requirements.txt
python app.py -i
deactivate