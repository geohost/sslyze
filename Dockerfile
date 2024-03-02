FROM python:3.13.0a4-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]