FROM pyaiot/base:latest

LABEL maintainer="alexandre.abadie@inria.fr"

ADD run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8000

CMD ["/run.sh"]
