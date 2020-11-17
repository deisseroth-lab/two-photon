#!/bin/bash
#
#SBATCH --job-name=bruker-rip
#
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=16G

if [ "$#" -ne 1 ]; then
   echo "Error! requires 1 argument: the directory containing the RAWDATA and FileList files."
   exit -1
fi

singularity run --bind=${1}:/data $OAK/pipeline/bruker-rip/containers/bruker-rip.sif
