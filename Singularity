# Singularity recipe file for d-lab two-photon container.

bootstrap: docker-daemon
from: scr.svc.stanford.edu/deisseroth-lab/bruker-rip:latest

%help
  First build the docker container:
    docker build -t scr.svc.stanford.edu/deisseroth-lab/bruker-rip:latest .
  Then build this file (assumes root as build directory):
    sudo singularity build two-photon.sif Singularity
  And run the rip script!
    singularity run --bind=/path/to/your/data:/data two-photon.sif

%runscript
  /bin/bash /apps/runscript.sh
