FROM python:3.13.0b1-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]