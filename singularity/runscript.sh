#!/bin/bash

TEMPDIR="$(mktemp -d)"
echo "Creating and changing into temporary directory $TEMPDIR..."
cd "$TEMPDIR"

APPDIR="/APPS"
PROFILEDIR="/PROFILES/${USER}@${HOSTNAME}"

# Prepare temporary wine prefix directory
echo "Setting up wine prefix..."
export WINEPREFIX="$TEMPDIR/wineprefix"
export WINEARCH="win64"

# If XVFB Server envars are not set, don't use it
if [ -z "XVFB_SERVER" ]; then
   wineboot --init
   winetricks -q vcrun2015
else
   xvfb-run wineboot --init
   xvfb-run winetricks -q vcrun2015
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

cd $TEMPDIR

# If a data directory is bound, process it
if [ -d "/data" ]; then
    echo "Detected /data folder bound!"
    echo "/usr/bin/python3 /app/rip.py --directory /data"

    # xvfb-run is needed for headless, otherwise, assume connection
    if [ -z "XVFB_SERVER" ]; then
        env WINEPREFIX="$WINEPREFIX" WINEARCH="$WINEARCH" /usr/bin/python3 /app/rip.py --directory /data    
    else
        env WINEPREFIX="$WINEPREFIX" WINEARCH="$WINEARCH" xvfb-run /usr/bin/python3 /app/rip.py --directory /data    
    fi

# Otherwise give an interactive terminal
else
    echo "Please install any software and use it! For an example"
    echo "To install Broken Sword 2.5 (download size ~700MB):"
    echo " wget http://server.c-otto.de/baphometsfluch/bs25setup.zip"
    echo " unzip bs25setup.zip"
    echo " wine ./bs25-setup.exe"
    echo
    echo "To run the two-photon ripper:"
    echo "/usr/bin/python3 /app/rip.py --directory /data"
    echo "You'll need to use xvfb-run if you don't have a display."
    env WINEPREFIX="$WINEPREFIX" WINEARCH="$WINEARCH" /bin/bash
fi

wineboot --end-session

cd /
rm -rf "$TEMPDIR"
