FROM python:3.13.0rc2-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]