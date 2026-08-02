FROM mambaorg/micromamba:1.5.8

COPY environment.yml /tmp/environment.yml
RUN micromamba env create -f /tmp/environment.yml && \
    micromamba clean --all --yes
ENV PATH=/opt/conda/bin:$PATH
WORKDIR /workspace
COPY . /workspace
CMD ["/bin/bash"]
