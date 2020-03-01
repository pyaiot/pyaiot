FROM pyaiot/base:latest

MAINTAINER Alexandre Abadie <alexandre.abadie@inria.fr>

ADD run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 5683/udp

CMD ["/run.sh"]
