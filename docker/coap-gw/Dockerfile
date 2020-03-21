FROM pyaiot/base:latest

LABEL maintainer="alexandre.abadie@inria.fr"

ADD run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 5683/udp

CMD ["/run.sh"]
