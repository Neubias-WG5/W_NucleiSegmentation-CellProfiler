FROM neubiaswg5/cellprofiler-base:latest
FROM cytomineuliege/software-python3-base:latest

ADD wrapper.py /app/wrapper.py
ADD CP_detect_nuclei.cppipe /cp/CP_detect_nuclei.cppipe
WORKDIR /CellProfiler

ENTRYPOINT ["cellprofiler"]
#["python", "/app/wrapper.py"]
