#!/bin/bash

./manage.py reset django_census django_stock --noinput
./manage.py loaddata ./django_census/fixtures/most_recent.json ./django_stock/fixtures/most_recent.json

