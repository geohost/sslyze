FROM python:3.13.0b4-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]