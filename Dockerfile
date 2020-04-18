FROM python:3.6
MAINTAINER Zach White <skullydazed@gmail.com>
EXPOSE 5001

WORKDIR /qmk_api
COPY . /qmk_api
RUN pip3 install -r requirements.txt git+git://github.com/qmk/qmk_compiler.git@master git+git://github.com/skullydazed/kle2xy.git@master
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
CMD ./run
