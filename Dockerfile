FROM python:3.14.0a3-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]