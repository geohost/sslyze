FROM python:3.13.0b2-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]