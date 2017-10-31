FROM debian
MAINTAINER Zach White <skullydazed@gmail.com>

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    gcc \
    git \
    python3 \
    python3-pip \
    python3-setuptools \
    unzip \
    wget \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
RUN git clone https://github.com/qmk/qmk_compiler_api.git
WORKDIR /qmk_compiler_api
RUN pip3 install git+git://github.com/qmk/qmk_compiler_worker.git@master
RUN pip3 install -r requirements.txt
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
CMD gunicorn -w 8 -b 0.0.0.0:5000 --max-requests 1000 --max-requests-jitter 100 -t 60 --access-logfile=- web:app
