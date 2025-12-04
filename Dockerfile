FROM python:3.14.1-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]