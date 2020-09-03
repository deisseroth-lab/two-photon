#!/bin/bash

# The container executable.  This script takes no arguments, and just performs 
# minimal environment setup prior to running main script.

set -e

echo "Setting up wine environment"
TEMPDIR="$(mktemp -d)"
export WINEPREFIX="${TEMPDIR}/.wine"
export WINEARCH="win64"
cp -r /home/wineuser/.wine "${WINEPREFIX}"
echo

echo "Executing rip.  It is OK to see 1 'err' and 4 'fixme' statements in what follows."
echo
# USE_XVFB means xvfb is already running.  If it is unset, xvfb needs to be run here.
if [[ -z "${USE_XVFB}" ]]; then
    xvfb-run /usr/bin/python3 /apps/two-photon/rip.py --directory /data
else
    /usr/bin/python3 /apps/two-photon/rip.py --directory /data
fi
