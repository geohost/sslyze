FROM python:3.14.0a1-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]