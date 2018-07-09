FROM neubiaswg5/cellprofiler-base:latest

ADD wrapper.py /app/wrapper.py

ENTRYPOINT ["python", "/app/wrapper.py"]
