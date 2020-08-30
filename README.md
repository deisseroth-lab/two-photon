# two-photon

First, install the code.  You can use [GitHub desktop](https://desktop.github.com/), or use git on the command line:

```bash
git clone https://github.com/deisseroth-lab/two-photon.git
```

Next, install the environment.  You will need to install [conda](https://docs.conda.io/en/latest/) first.  Then
use the following command from within the directory where you installed the repo above.

```bash
conda env create -f environment.yml -n two-photon
```

To run the processing script, the environment needs to be activated:
```
conda activate two-photon
```

See the comments at the top of the [preprocess script](https://github.com/deisseroth-lab/two-photon/blob/master/process.py)
for examples of how to run the processing.

## Docker for ripping only

To build the docker container and tag it as `two-photon:latest`, use:

```bash
docker build -t two-photon .
```

Run the ripper using the following command, using a directory containin the *RAWDATA* and *FileList.txt files.

```bash
./docker_rip.sh /media/hdd0/two-photon/sample/overview-023
```

## Singularity for ripping only

To build the Singularity container, build the Docker container first and then convert:

```bash
docker build -t two-photon .
singularity build two-photon.sif docker-daemon://two-photon:latest
```

Run the ripper using the following command, using a directory containin the *RAWDATA* and *FileList.txt files.

_NB: Does not work_

```bash
./singularity_rip.sh /media/hdd0/two-photon/sample/overview-023
```
