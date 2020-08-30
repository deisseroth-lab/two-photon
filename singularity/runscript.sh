#!/bin/bash

TEMPDIR="$(mktemp -d)"
echo "Creating and changing into temporary directory $TEMPDIR..."
cd "$TEMPDIR"

APPDIR="/APPS"
PROFILEDIR="/PROFILES/${USER}@${HOSTNAME}"

echo "Setting up wine prefix..."
export WINEPREFIX="$TEMPDIR/wineprefix"
export WINEARCH="win64"

if [[ -f "$APPDIR/wineprefix.tgz" ]]; then
    echo "Found existing wineprefix - restoring it..."
    mkdir -p "$WINEPREFIX"
    cd "$WINEPREFIX"
    tar xzf "$APPDIR/wineprefix.tgz"
else
  wineboot --init

  echo "Installing DirectX9..."
  winetricks dlls d3dx9

  echo "Installing C++ libraries..."
  winetricks -q vcrun2015

fi

echo "Containerizing apps directory..."
if [[ -L "$WINEPREFIX/drive_c/Apps" ]]; then
    echo "Link exists already"
else
    ln -sf "$APPDIR" "$WINEPREFIX/drive_c/Apps"
    echo "Link created"
fi

echo "Containerizing user profile..."
if [[ -d "$PROFILEDIR" ]]; then
    rm -rf "$WINEPREFIX/drive_c/users/$USER"
else
    echo "This user profile is newly generated..."
    mv "$WINEPREFIX/drive_c/users/$USER" "$PROFILEDIR"
fi
ln -s "$PROFILEDIR" "$WINEPREFIX/drive_c/users/$USER"

echo "Please install any software and use it! For an example"
echo "To install Broken Sword 2.5 (download size ~700MB):"
echo " wget http://server.c-otto.de/baphometsfluch/bs25setup.zip"
echo " unzip bs25setup.zip"
echo " wine ./bs25-setup.exe"
echo
echo "To run the two-photon ripper:"
echo "/usr/bin/python3 /app/rip.py --directory /data"
cd $TEMPDIR
env WINEPREFIX="$WINEPREFIX" WINEARCH="$WINEARCH" /bin/bash

wineboot --end-session

cd /
rm -rf "$TEMPDIR"
