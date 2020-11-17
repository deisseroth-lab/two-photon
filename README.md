# two-photon

This repository contains utilities for analyzing 2p data:

- [Ripping](#ripping)
- [Suite2p Pipeline](#suite2p-pipeline)

## Ripping

Ripping is the process for converting a Bruker RAWDATA file into a set of TIFF files.

The lab has created [Docker](https://www.docker.com/) and
[Singularity](https://sylabs.io/docs/) containers with the Bruker Prairie View software,
which can be used to rip raw data computers with either set of container software installed.

### Ripping via Singularity

If you would like to run from a container on [Sherlock](https://www.sherlock.stanford.edu/),
the lab keeps a copy available in \$OAK/pipeline/bruker-rip/containers.

Here's a quick demo:

```bash
$ mkdir -p $OAK/users/${USER}/test
$ cp -r $OAK/pipeline/bruker-rip/sampledata/overview-023 $OAK/users/${USER}/test
$ chmod 777 $OAK/users/${USER}/test/* # we need write permissions to convert the file
$ singularity run \
    --bind=$OAK/users/${USER}/test/overview-023:/data \
    $OAK/pipeline/bruker-rip/containers/bruker-rip.sif
```

Here's how to run on your own data. We request a node allocation using `sdev` as
long-running jobs should not use login nodes.

```bash
$ cd my/data/path
$ sdev  # May take some time to get a machine for development use
$ singularity run --bind=$(pwd):/data $OAK/pipeline/bruker-rip/containers/bruker-rip.sif
```

Here is an example run for a local machine:

```bash
$ singularity run --bind=/media/hdd0/two-photon/sample/overview-023:/data bruker-rip.sif
Setting up wine environment

Executing rip.  It is OK to see 1 err and 4 fixme statements in what follows

2020-09-03 16:59:07.566 rip:50 INFO Ripping from:
 /data/Cycle00001_Filelist.txt
 /data/CYCLE_000001_RAWDATA_000025
2020-09-03 16:59:07.581 rip:96 INFO Waiting for ripper to finish: 3600 seconds remaining
000d:err:menubuilder:init_xdg error looking up the desktop directory
0031:fixme:ntdll:EtwEventRegister ({5eec90ab-c022-44b2-a5dd-fd716a222a15}, 0xd4c1000, 0xd4d2030, 0xd4d2050) stub.
0031:fixme:ntdll:EtwEventSetInformation (deadbeef, 2, 0xd4cfd70, 43) stub
0031:fixme:nls:GetThreadPreferredUILanguages 00000038, 0xdb0cdb4, 0xdb0cdd0 0xdb0cdb0
0031:fixme:nls:get_dummy_preferred_ui_language (0x38 0xdb0cdb4 0xdb0cdd0 0xdb0cdb0) returning a dummy value (current locale)
2020-09-03 16:59:17.592 rip:107 INFO   Found filelist files: None
2020-09-03 16:59:17.592 rip:108 INFO   Found rawdata files: None
2020-09-03 16:59:17.592 rip:109 INFO   Found this many tiff files: 1
2020-09-03 16:59:17.592 rip:96 INFO Waiting for ripper to finish: 3590 seconds remaining
2020-09-03 16:59:27.603 rip:107 INFO   Found filelist files: None
2020-09-03 16:59:27.603 rip:108 INFO   Found rawdata files: None
2020-09-03 16:59:27.603 rip:109 INFO   Found this many tiff files: 1
2020-09-03 16:59:27.604 rip:112 INFO Detected ripping is complete
2020-09-03 16:59:37.614 rip:114 INFO Killing ripper
2020-09-03 16:59:37.614 rip:116 INFO Ripper has been killed
2020-09-03 16:59:38.616 rip:88 INFO cleaned up!
X connection to :99 broken (explicit kill or server shutdown).
```

### Ripping via Docker

You can run on a device with Docker installed using the command below. The image
will be available locally if you've build from source (see below), or it will be
fetched from the the [Stanford GitLab](https://code.stanford.edu/deisseroth-lab/bruker-rip). Contact croat@stanford.edu if you need access.

```bash
$ ./rip_docker.sh \
    scr.svc.stanford.edu/deisseroth-lab/bruker-rip:20200903 \
    /path/to/data/with/filelist/and/rawdata/
```

Example run:

```bash
$ ./rip_docker.sh \
    scr.svc.stanford.edu/deisseroth-lab/bruker-rip:20200903 \
    /media/hdd0/two-photon/sample/overview-023
Setting up wine environment

Executing rip.  It is OK to see 1 err and 4 fixme statements in what follows

2020-09-03 14:41:33.936 rip:50 INFO Ripping from:
 /data/Cycle00001_Filelist.txt
 /data/CYCLE_000001_RAWDATA_000025
2020-09-03 14:41:33.940 rip:96 INFO Waiting for ripper to finish: 3600 seconds remaining
000d:err:menubuilder:init_xdg error looking up the desktop directory
0031:fixme:ntdll:EtwEventRegister ({5eec90ab-c022-44b2-a5dd-fd716a222a15}, 0xd441000, 0xd452030, 0xd452050) stub.
0031:fixme:ntdll:EtwEventSetInformation (deadbeef, 2, 0xd44fd70, 43) stub
0031:fixme:nls:GetThreadPreferredUILanguages 00000038, 0xdaacdb4, 0xdaacdd0 0xdaacdb0
0031:fixme:nls:get_dummy_preferred_ui_language (0x38 0xdaacdb4 0xdaacdd0 0xdaacdb0) returning a dummy value (current locale)
2020-09-03 14:41:43.951 rip:107 INFO   Found filelist files: None
2020-09-03 14:41:43.951 rip:108 INFO   Found rawdata files: None
2020-09-03 14:41:43.951 rip:109 INFO   Found this many tiff files: 1
2020-09-03 14:41:43.951 rip:96 INFO Waiting for ripper to finish: 3590 seconds remaining
2020-09-03 14:41:53.962 rip:107 INFO   Found filelist files: None
2020-09-03 14:41:53.962 rip:108 INFO   Found rawdata files: None
2020-09-03 14:41:53.962 rip:109 INFO   Found this many tiff files: 1
2020-09-03 14:41:53.963 rip:112 INFO Detected ripping is complete
2020-09-03 14:42:03.973 rip:114 INFO Killing ripper
2020-09-03 14:42:03.973 rip:116 INFO Ripper has been killed
2020-09-03 14:42:04.975 rip:88 INFO cleaned up!
```

## Suite2p Pipeline

The analysis pipeline can run several steps of standard preprocessing of 2p data:

- rip
- preprocess to remove stim artefacts
- run Suite2p (optionally combining with previously preprocessed sessions)
- backup input data
- backup output data

First, install the code. You can use [GitHub desktop](https://desktop.github.com/), or use git on the command line. This only has to be done once.

```bash
git clone https://github.com/deisseroth-lab/two-photon.git
```

Next, install the environment. You will need to install [conda](https://docs.conda.io/en/latest/) first. Then
use the following command from within the directory where you installed the repo above. This also only has
to be done once.

```bash
conda env create -f environment.yml -n two-photon
```

To run the processing script, the environment needs to be activated. This needs to be done each time start a terminal.

```bash
conda activate two-photon
```

Running the code requires running a command-line program with flags to denote where the input data is, where the output
data and logs should go, and what stages of the pipeline should be run.

See the comments at the top of the [preprocess script](https://github.com/deisseroth-lab/two-photon/blob/master/app/process.py)
for examples of how to run the processing.

## Building Containers

To build all available containers, which will first build the Docker container, and then convert it
to a Singularity container:

```bash
make build
```

To build just the docker containers:

```bash
make build_docker
```

View the [Makefile](Makefile) for additional targets, including targets to build just build specific containers.
