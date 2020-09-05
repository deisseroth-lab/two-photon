# Builds Bruker ripping image.

# This docker-wine image is about 2 GB, mostly from:
# - 0.5 GB from Ubuntu packages
# - 1.5 GB from wine install
FROM scottyhardy/docker-wine:stable-5.0.2-nordp

LABEL maintainer="Chris Roat <croat@stanford.edu>"

# The entrypoint wrapper runs the wine setup as wineuser.
# The xvfb-run wrapper redirects all displays to a virtual (unseen) display.
# This adds about 1.6 GB to the image size.
RUN /usr/bin/entrypoint xvfb-run winetricks -q vcrun2015

ENV PATH /opt/conda/bin:$PATH

# Conda install is 250 MB
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

COPY ["Prairie View 5.5/", "/apps/Prairie View 5.5/"]

# Environment is ~700 MB
COPY environment.yml .
RUN conda env update --quiet --name base --file environment.yml \
    && conda clean --all -f -y \
    && rm environment.yml

# Copy code last to avoid busting the cache.
COPY two-photon/*.py /apps/two-photon/
COPY runscript.sh /apps/runscript.sh

CMD /apps/runscript.sh
