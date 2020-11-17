#!/bin/bash

# The container executable.  This script takes no arguments, and just performs 
# minimal environment setup prior to running main script.

set -e

# USE_XVFB means xvfb is already running.  If it is unset, xvfb-run should wrap commands.
[[ -z "${USE_XVFB}" ]] && CMDPREFIX=xvfb-run

echo
echo "Copying wine environment."
echo
TEMPDIR="$(mktemp -d)"
export WINEPREFIX="${TEMPDIR}/.wine"
export WINEARCH="win64"
cp -r /home/wineuser/.wine "${WINEPREFIX}"

echo "Executing rip. One err and four fixme statements are OK."
echo
${CMDPREFIX} /usr/bin/python3 /apps/two-photon/rip.py --directory /data "$@"
