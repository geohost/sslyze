FROM python:3.14.0rc2-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]