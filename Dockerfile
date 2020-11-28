FROM ubuntu:16.04

# Install CellProfiler
RUN apt-get update -y   && \
    apt-get upgrade -y  && \
    apt-get install -y     \
        build-essential    \
        cython             \
        git                \
        libmysqlclient-dev \
        libhdf5-dev        \
        libxml2-dev        \
        libxslt1-dev       \
        openjdk-8-jdk      \
	libssl-dev	   \
        python-dev         \
        python-pip         \
        python-scipy       \
        python-vigra       \
        python-wxgtk3.0    \
        python-zmq         \
	python-pytest

# These are needed to install cellh5 requirement of CellProfiler
RUN pip install --upgrade setuptools==38.0
# Specify versions that support Python2.7
RUN pip install numpy==1.14.0 && \
    pip install h5py==2.7.0 && \
    pip install networkx==2.2 && \
    pip install kiwisolver==1.0.1 && \
    pip install matplotlib==2.2.3 && \
    pip install PyWavelets==0.5.0 && \
    pip install pillow==5.0.0 && \
    pip install scikit-image==0.14.0 && \
    pip install pandas==0.24.2 && \
    pip install scikit-learn==0.20.1 && \
    pip install dask==1.2.2 && \
    pip install hmmlearn==0.2.2 && \
    pip install centrosome==1.0.4 && \
    pip install python-bioformats==1.5.0

RUN mkdir /app
RUN cd /app && git clone https://github.com/CellProfiler/CellProfiler.git
RUN cd /app/CellProfiler && git checkout 2.2.0 && python2.7 -m pip install --editable .

# Install Python3.7
RUN apt-get update -y && \
    apt-get install -y software-properties-common python-software-properties

RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update -y && \
    apt-get install -y python3.7 && \
    apt-get install -y python3.7-dev && \
    apt-get install -y python3.7-venv && \
    apt-get install -y wget

RUN cd /tmp && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.7 get-pip.py

RUN pip3 install requests \
    requests-toolbelt \
    six \
    future \
    shapely \
    opencv-python \
    scikit-image

# Install Cytomine Python client
RUN cd / && \
    git clone https://github.com/cytomine-uliege/Cytomine-python-client.git && \
    cd Cytomine-python-client && \
    git checkout tags/v2.7.3 && \
    pip3 install .

# Install NEUBIAS WG5 Utilities
RUN apt-get update && apt-get install libgeos-dev -y && apt-get clean
RUN git clone https://github.com/Neubias-WG5/biaflows-utilities.git && \
    cd /biaflows-utilities/ && git checkout tags/v0.9.1 && pip install .

RUN chmod +x /biaflows-utilities/bin/*
RUN cp /biaflows-utilities/bin/* /usr/bin/
RUN rm -r /biaflows-utilities

ADD wrapper.py /app/wrapper.py
ADD CP_detect_nuclei.cppipe /app/CP_detect_nuclei.cppipe
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.7","/app/wrapper.py"]
