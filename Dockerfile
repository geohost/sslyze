FROM python:3.14.0rc1-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]