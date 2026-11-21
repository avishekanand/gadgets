#!/bin/bash
# Export every printable part of Pip the dog as STL (in print orientation) + preview images.
#   ./build.sh            -> stl/*.stl and renders/*.png
# Needs OpenSCAD (development snapshot recommended: brew install --cask openscad@snapshot).
set -e
cd "$(dirname "$0")"
mkdir -p stl renders
PARTS="front_plate body collar head_top head_bottom ear_left ear_right base tail neck_peg"
for p in $PARTS; do
  echo "  $p"
  openscad --backend=manifold -D "part=\"$p\"" -o "stl/$p.stl" pip_dog.scad 2>&1 | grep -iE "^error|warning" || true
done
for v in assembly exploded; do
  openscad --backend=manifold -D "part=\"$v\"" --imgsize=1100,1300 --viewall --autocenter \
    --camera=0,0,0,70,0,25,0 --colorscheme=Tomorrow -o "renders/$v.png" pip_dog.scad 2>/dev/null
done
openscad --backend=manifold -D 'part="assembly"' --imgsize=1100,1300 --viewall --autocenter \
  --camera=0,0,0,72,0,150,0 --colorscheme=Tomorrow -o renders/assembly_back.png pip_dog.scad 2>/dev/null
echo "done: stl/ and renders/"
