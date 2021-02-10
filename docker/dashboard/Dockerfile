ARG DOCKERHUB_REGISTRY="pyaiot"
FROM ${DOCKERHUB_REGISTRY}/base:latest


LABEL maintainer="alexandre.abadie@inria.fr"

RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_13.x | bash -
RUN apt-get install -y nodejs

ARG GIT_REMOTE="pyaiot"
RUN cd /opt && git clone https://github.com/${GIT_REMOTE}/pyaiot
RUN cd /opt/pyaiot/pyaiot/dashboard/static && npm install && cd

ADD run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8080

CMD ["/run.sh"]
