FROM neubiaswg5/cellprofiler-base:latest

#RUN pip uninstall annotation-exporter -y
#RUN pip install https://github.com/Neubias-WG5/AnnotationExporter/archive/master.zip

ADD wrapper.py /app/wrapper.py
ADD CP_detect_nuclei.cppipe /app/CP_detect_nuclei.cppipe

WORKDIR /app

ENTRYPOINT ["python3.6","wrapper.py"]
