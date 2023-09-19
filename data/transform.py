#!/usr/bin/env python

from sys import argv
from os.path import exists
import json as simplejson

script, in_file, out_file = argv

data = simplejson.load(open(in_file))

geojson = {
    "type": "FeatureCollection",
    "features": [
    {
        "type": "Feature",
        "geometry" : {
            "type": "Point",
            "coordinates": [d["longitude"], d["latitude"]],
            },
        "properties" : d,
     } for d in data]
}

output = open(out_file, 'w')
simplejson.dump(geojson, output)

print(geojson)
