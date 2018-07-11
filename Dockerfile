FROM neubiaswg5/cellprofiler-base:latest

ADD wrapper.py /app/wrapper.py
ADD CP_detect_nuclei.cppipe /app/CP_detect_nuclei.cppipe

WORKDIR /app
ENTRYPOINT ["python3.6","wrapper.py"]
