FROM python:3.13-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]