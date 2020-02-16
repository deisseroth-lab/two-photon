ARG BASE_CONTAINER=jupyter/scipy-notebook
FROM $BASE_CONTAINER

LABEL maintainer="Chris Roat <croat@stanford.edu>"

USER $NB_UID

# Install suite2p and dependencies
COPY environment.yml .environment.yml
RUN conda env update --quiet --name base --file .environment.yml

# Additional dependencies.
RUN conda install --quiet --yes \
    'pytables=3.6.1'

RUN conda clean --all -f -y && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/$NB_USER
