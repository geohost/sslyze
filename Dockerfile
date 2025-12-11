FROM python:3.14.2-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]