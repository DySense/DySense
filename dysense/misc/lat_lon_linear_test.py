# Find distances using method one#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import utm
import math

# All coordinates from google maps, same with distances in comments

# 1811 Platt St
home_lat = 39.190891
home_long = -96.586010

# Reference positions Lat, Long, Distance in feet measured on google maps
refs = [(39.191116, -96.586078, 100), # north
        (39.193584, -96.586044, 1000), # north
        (39.263176, -96.586327, 26400), # north
        (39.191233, -96.582579, 1000) # east
        ]

# Find linear relationship using method 1
#meters_per_deg_lat = (111132.92-559.82*math.cos(2*home_lat*math.pi / 180)+1.175*math.cos(4*home_lat*math.pi / 180))
#meters_per_deg_long = (111412.84*math.cos(home_lat*math.pi / 180) - 93.5*math.cos(3*home_lat*math.pi / 180))

ref_lat = home_lat * math.pi / 180.0
meters_per_deg_lat = 111132.92 - 559.82*math.cos(2.0*ref_lat) + 1.175*math.cos(4.0*ref_lat) - 0.0023*math.cos(6*ref_lat)
meters_per_deg_long = 111412.84*math.cos(ref_lat) - 93.5*math.cos(3.0*ref_lat) + 0.118*math.cos(5.0*ref_lat)

# Distances for method 1
dist1 = [] # local
for ref_pos in refs:
    delta_north = (ref_pos[0] - home_lat) * meters_per_deg_lat
    delta_east = (ref_pos[1] - home_long) * meters_per_deg_long
    dist1.append((delta_north, delta_east))

# Find distances using method 2
east_home, north_home, _, _ = utm.from_latlon(home_lat, home_long)
dist2 = [] # local
dist2_utm = [] # UTM
for ref_pos in refs:
    east_ref, north_ref, zone_num, zone_letter = utm.from_latlon(ref_pos[0], ref_pos[1])
    delta_north = north_ref - north_home
    delta_east = east_ref - east_home
    dist2.append((delta_north, delta_east))

    dist2_utm.append((east_ref, north_ref))

print "Errors (linear - UTM) in meters"
for d1, d2 in zip(dist1, dist2):
    north_error = d1[0] - d2[0]
    east_error = d1[1] - d2[1]
    print (north_error, east_error)

# Add in an offset to represent sensor offset
offset_east = 0
offset_north = 0
dist1_off = [(d[0] + offset_north, d[1] + offset_east) for d in dist1]
dist2_utm_off = [(d[0] + offset_east, d[1] + offset_north) for d in dist2_utm]

# Convert these back to lat/long
ref1_off = []
for d1_off in dist1_off:
    lat = d1_off[0] / meters_per_deg_lat + home_lat
    long = d1_off[1] / meters_per_deg_long + home_long
    ref1_off.append((lat, long))

ref2_off = []
for d2_off in dist2_utm_off:
    lat, long = utm.to_latlon(d2_off[0], d2_off[1], zone_num, zone_letter)
    ref2_off.append((lat, long))

# Now calculate the error between these two methods
print "Offset Errors (north, east)"
for r1_off, r2_off in zip(ref1_off, ref2_off):
    diff_lat = r1_off[0] - r2_off[0]
    diff_long = r1_off[1] - r2_off[1]

    # Convert these back to meters for a reference
    ref_lat = r1_off[0] * math.pi / 180.0
    meters_per_deg_lat_at_ref = 111132.92 - 559.82*math.cos(2.0*ref_lat) + 1.175*math.cos(4.0*ref_lat) - 0.0023*math.cos(6*ref_lat)
    meters_per_deg_long_at_ref = 111412.84*math.cos(ref_lat) - 93.5*math.cos(3.0*ref_lat) + 0.118*math.cos(5.0*ref_lat)

    diff_north = diff_lat * meters_per_deg_lat_at_ref
    diff_east = diff_long * meters_per_deg_long_at_ref

    print (diff_north, diff_east)

#print meters_per_deg_lat
#print meters_per_deg_long

print "Error going from lat/long -> UTM and back in meters."
# Brazil lat long
home_lat = 40
home_long = -96
ref_lat = home_lat * math.pi / 180.0
meters_per_deg_lat = 111132.92 - 559.82*math.cos(2.0*ref_lat) + 1.175*math.cos(4.0*ref_lat) - 0.0023*math.cos(6*ref_lat)
meters_per_deg_long = 111412.84*math.cos(ref_lat) - 93.5*math.cos(3.0*ref_lat) + 0.118*math.cos(5.0*ref_lat)
e, n, zone_num, zone_letter = utm.from_latlon(home_lat, home_long)
new_lat, new_long = utm.to_latlon(e, n, zone_num, zone_letter)
diff_lat = (new_lat - home_lat)
diff_long = (new_long - home_long)
print "Diff Lat {} ".format(diff_lat)
print "Diff long {}".format(diff_long)
print "North {}".format(diff_lat * meters_per_deg_lat)
print "East {}".format( diff_long * meters_per_deg_long)


