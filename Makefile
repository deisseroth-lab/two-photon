build: build_docker
	rm -f two-photon.sif
	sudo singularity build two-photon.sif Singularity

build_docker:
	docker build -t dlab/two-photon .

