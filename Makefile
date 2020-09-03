all: docker docker_build

docker:
	docker build -t dlab/two-photon .

singularity:
	rm -f two-photon.sif
	sudo singularity build two-photon.sif Singularity
