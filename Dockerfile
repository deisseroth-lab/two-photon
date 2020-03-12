FROM continuumio/miniconda:4.7.12

LABEL maintainer="Chris Roat <croat@stanford.edu>"

# Install necessary software.
COPY environment.yml .
RUN conda env update --quiet --name base --file environment.yml \
    && conda clean --all -f -y

# Copy code last to avoid busting the cache.
COPY *.py .

ENTRYPOINT ["python", "process.py"]
CMD []
