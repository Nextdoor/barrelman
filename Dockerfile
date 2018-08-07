FROM python:3.6.5-stretch
ENTRYPOINT ["/app/entrypoint.sh"]
EXPOSE 80 443

# Set up nginx and openssl.
RUN apt-get update && \
    apt-get install -y nginx && \
    apt-get clean -y

# Generate SSL certs.
RUN mkdir -p /app/ssl && cd /app/ssl && \
    openssl req -x509 -nodes -newkey rsa:4096 -sha256 \
                -keyout privkey.pem -out fullchain.pem \
                -days 36500 -subj '/CN=localhost' && \
    openssl dhparam -dsaparam -out dhparam.pem 4096

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt && pip freeze

ADD secrets/ /app/secrets
ADD resources/ /app
ADD src/ /app/src
