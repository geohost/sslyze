FROM python:3.13.0b3-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]