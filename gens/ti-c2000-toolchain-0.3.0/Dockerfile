FROM python:3.12-slim
WORKDIR /work
COPY . /work
RUN pip install --no-cache-dir -e .
ENTRYPOINT ["ti-svd"]
CMD ["list"]
