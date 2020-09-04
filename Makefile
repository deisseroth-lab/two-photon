REPO=scr.svc.stanford.edu/deisseroth-lab
TAG=20200903
NAME=bruker-rip

build: build_docker build_singularity

push: push_docker push_singularity

build_docker:
	docker build -t $(REPO)/$(NAME):$(TAG) .
	docker tag $(REPO)/$(NAME):$(TAG) $(REPO)/$(NAME):latest

build_singularity:
	rm -f $(NAME).$(TAG).sif
	sudo singularity build $(NAME).$(TAG).sif Singularity

push_docker:
	docker push $(REPO)/$(NAME):$(TAG)
	docker push $(REPO)/$(NAME):latest

push_singularity:
	$(info )
	$(info Wait a few seconds -- you will need to provide your SUNet password for Sherlock access)
	$(info )
	rsync --archive --human-readable --progress --verbose \
		$(NAME).$(TAG).sif dtn.sherlock.stanford.edu:/oak/stanford/groups/deissero/pipeline/bruker-rip/containers/
