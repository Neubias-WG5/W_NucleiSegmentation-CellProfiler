FROM neubiaswg5/cellprofiler-base:v0.1

ADD wrapper.py /app/wrapper.py

ENTRYPOINT ["python", "/app/wrapper.py"]
