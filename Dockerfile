FROM python:3.12.11-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]