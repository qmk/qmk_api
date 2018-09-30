#!/usr/bin/env python3
import json
import svgwrite

from sys import argv

infoFile = argv[1]
with open(infoFile) as f:
    data = json.load(f)


# "x":0,
# "y":0,
# "w":1,
# "label":"GRAVE"

# def keycap_oem(dwg, x, y, w):
#     dwg.add(dwg.rect(insert=(x*20, y*20), size=(w, 1), rx=1, ry=1))


dwg = svgwrite.Drawing('test.svg', profile='full')
keycaps = {}

for i in range(0, 36):
    w = (i * .25) + 1
    keycaps[int(w*4)] = dwg.defs.add(dwg.g(id='g'+str(w)))
    keycaps[int(w*4)].add(dwg.rect(
        insert=(0, 0), 
        size=((20 * w) - 1, 19), rx=1.5, ry=1.5, 
        fill=svgwrite.rgb(240, 240, 240)))
    keycaps[int(w*4)].add(dwg.rect(
        insert=(0.5, 0.5), 
        size=((20 * w) - 2, 18), rx=1, ry=1,
        fill_opacity=0).stroke(svgwrite.rgb(200, 200, 200),
        width=1))
    keycaps[int(w*4)].add(dwg.rect(
        insert=(3, 2),
        size=((20 * w) - 7, 14), rx=1, ry=1, 
        fill=svgwrite.rgb(255, 255, 255)))

max_x = 0
max_y = 0
max_w = 0

padding = [2, 2, 2, 2]
radius = [2, 2, 2, 2]

if ('display' in data):
    padding = [int(x) for x in data['display']['padding'].split(' ')]
    radius = [int(x) for x in data['display']['radius'].split(' ')]

for key in data['layouts']['KEYMAP']['layout']:
    k = dwg.use(keycaps[int(key['w']*4)], insert=(key['x']*20 + padding[3], key['y']*20 + padding[0]))
    dwg.add(k)
    if (key['y'] >= max_y):
        max_y = key['y']
    if (key['x'] >= max_x):
        max_x = key['x']
        if (key['w'] >= max_w):
            max_w = key['w']

dwg.add(dwg.rect(insert=(0, 0), 
    size=((max_x+max_w)*20 + padding[1] + padding[3], (max_y+1)*20 + padding[0] + padding[2]), fill_opacity=0, rx=radius[0], ry=radius[1]).stroke(
    svgwrite.rgb(200, 200, 200), width=1))

dwg.save()