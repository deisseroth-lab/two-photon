FROM scottyhardy/docker-wine:stable-5.0.2-nordp

LABEL maintainer="Chris Roat <croat@stanford.edu>"

RUN xvfb-run winetricks -q vcrun2015

COPY ["Prairie View/", "/Prairie View/"]

ENV PATH /opt/conda/bin:$PATH

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

COPY environment.yml .
RUN conda env update --quiet --name base --file environment.yml \
    && conda clean --all -f -y \
    && rm environment.yml

# Copy code last to avoid busting the cache.
COPY *.py /app/
