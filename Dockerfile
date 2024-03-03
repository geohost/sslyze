FROM python:3.13.0a3-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]