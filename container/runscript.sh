#!/bin/bash
#
# The container executable.  This script takes no arguments, and just performs 
# minimal environment setup prior to running main script.

TEMPDIR="$(mktemp -d)"

export WINEPREFIX="${TEMPDIR}/.wine"
export WINEARCH="win64"

echo copying wine environment
cp -r /home/wineuser/.wine "${WINEPREFIX}"

/usr/bin/python3 /apps/two-photon/rip.py --directory /data    
