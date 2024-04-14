FROM python:3.13.0a6-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]