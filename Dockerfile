FROM ubuntu:latest
LABEL authors="teppler"

ENTRYPOINT ["top", "-b"]