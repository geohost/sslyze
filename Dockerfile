FROM python:3.14.3-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]