FROM python:3.8.18-slim
RUN pip install sslyze
ENTRYPOINT ["sslyze"]
CMD ["-h"]