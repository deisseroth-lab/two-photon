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

```bash
$ ./rip_singularity.sh \
    $OAK/pipeline/bruker-rip/containers/bruker-rip.20200903.sif \
    /path/to/data/with/filelist/and/rawdata/

# or run directly without the shell script:
singularity run \
    --bind=/path/to/data/with/filelist/and/rawdata/:/data \
    $OAK/pipeline/bruker-rip/containers/bruker-rip.20200903.sif
```

Here is an example run on sample data on the Sherlock cluster:

```bash
# After logging into Sherlock
$ sdev  # May take some time to get a machine for development use
$ mkdir -p $OAK/users/${USER}/test
$ cp -r $OAK/pipeline/bruker-rip/sampledata/overview-023 $OAK/users/${USER}/test
$ singularity run \
    --bind=$OAK/users/${USER}/test/overview-023:/data \
    $OAK/pipeline/bruker-rip/containers/bruker-rip.20200903.sif
Setting up wine environment

Executing rip.  It is OK to see 1 err and 4 fixme statements in what follows

2020-09-03 16:34:51.336 rip:50 INFO Ripping from:
 /data/Cycle00001_Filelist.txt
 /data/CYCLE_000001_RAWDATA_000025
2020-09-03 16:34:51.393 rip:96 INFO Waiting for ripper to finish: 3600 seconds remaining
000d:err:menubuilder:init_xdg error looking up the desktop directory
0033:fixme:ntdll:EtwEventRegister ({5eec90ab-c022-44b2-a5dd-fd716a222a15}, 0x70e1000, 0x70f2030, 0x70f2050) stub.
0033:fixme:ntdll:EtwEventSetInformation (deadbeef, 2, 0x70efd70, 43) stub
0033:fixme:nls:GetThreadPreferredUILanguages 00000038, 0x772cdb4, 0x772cdd0 0x772cdb0
0033:fixme:nls:get_dummy_preferred_ui_language (0x38 0x772cdb4 0x772cdd0 0x772cdb0) returning a dummy value (current locale)

=================================================================
	Native Crash Reporting
=================================================================
Got a SIGSEGV while executing native code. This usually indicates
a fatal error in the mono runtime or one of the native libraries
used by your application.
=================================================================

=================================================================
	Managed Stacktrace:
=================================================================
	  at <unknown> <0xffffffff>
	  at Image_Block_Ripping_Utility.frmMain:RipRawImages <0x000e5>
	  at Image_Block_Ripping_Utility.frmMain:StartConversion <0x009ca>
	  at System.Threading.ThreadHelper:ThreadStart_Context <0x000b2>
	  at System.Threading.ExecutionContext:RunInternal <0x001f5>
	  at System.Threading.ExecutionContext:Run <0x00052>
	  at System.Threading.ExecutionContext:Run <0x0007a>
	  at System.Threading.ThreadHelper:ThreadStart <0x0005a>
	  at System.Object:runtime_invoke_void__this__ <0x0009f>
=================================================================
wine: Unhandled page fault on read access to 0000000000000050 at address 000000007BC519B5 (thread 0033), starting debugger...
2020-09-03 16:35:01.398 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:01.398 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:01.399 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:01.399 rip:96 INFO Waiting for ripper to finish: 3590 seconds remaining
2020-09-03 16:35:11.406 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:11.407 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:11.407 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:11.407 rip:96 INFO Waiting for ripper to finish: 3580 seconds remaining
2020-09-03 16:35:21.413 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:21.414 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:21.414 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:21.414 rip:96 INFO Waiting for ripper to finish: 3570 seconds remaining
2020-09-03 16:35:31.419 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:31.419 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:31.419 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:31.419 rip:96 INFO Waiting for ripper to finish: 3560 seconds remaining
2020-09-03 16:35:41.430 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:41.430 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:41.431 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:41.431 rip:96 INFO Waiting for ripper to finish: 3550 seconds remaining
2020-09-03 16:35:51.442 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:35:51.442 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:35:51.443 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:35:51.443 rip:96 INFO Waiting for ripper to finish: 3540 seconds remaining
2020-09-03 16:36:01.453 rip:107 INFO   Found filelist files: {PosixPath('/data/Cycle00001_Filelist.txt')}
2020-09-03 16:36:01.453 rip:108 INFO   Found rawdata files: {PosixPath('/data/CYCLE_000001_RAWDATA_000025')}
2020-09-03 16:36:01.453 rip:109 INFO   Found this many tiff files: 0
2020-09-03 16:36:01.453 rip:96 INFO Waiting for ripper to finish: 3530 seconds remaining
^CTraceback (most recent call last):
  File "/apps/two-photon/rip.py", line 135, in <module>
    raw_to_tiff(args.directory, args.ripper)
X connection to :99 broken (explicit kill or server shutdown).
  File "/apps/two-photon/rip.py", line 98, in raw_to_tiff
    time.sleep(RIP_POLL_SECS)
KeyboardInterrupt
2020-09-03 16:36:11.556 rip:88 INFO cleaned up!
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

```
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
