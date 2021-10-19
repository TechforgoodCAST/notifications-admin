FROM python:3.6-alpine

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache bash build-base libxml2-dev libxslt-dev git nodejs npm g++ make libffi-dev gcc musl-dev python3-dev libffi-dev openssl-dev cargo && rm -rf /var/cache/apk/*

RUN apk add --virtual .build-deps \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        gcc libc-dev geos-dev geos && \
    runDeps="$(scanelf --needed --nobanner --recursive /usr/local \
    | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
    | xargs -r apk info --installed \
    | sort -u)" && \
    apk add --virtual .rundeps $runDeps

RUN geos-config --cflags

# update pip
RUN python -m pip install wheel

# -- Install Application into container:
RUN set -ex && mkdir /app

WORKDIR /app

COPY requirements.txt /app
RUN set -ex && pip3 install -r requirements.txt

COPY package.json package-lock.json /app/
RUN npm ci

COPY . /app

RUN npm run build

ENV PORT=6012

CMD ["sh", "-c", "gunicorn -c gunicorn_config.py application"]