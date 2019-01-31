FROM neubiaswg5/cellprofiler-base

ADD wrapper.py /app/wrapper.py
ADD CP_detect_nuclei.cppipe /app/CP_detect_nuclei.cppipe

ENTRYPOINT ["python3.6","/app/wrapper.py"]
