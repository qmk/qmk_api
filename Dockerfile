FROM python:3.9
MAINTAINER Zach White <skullydazed@gmail.com>
EXPOSE 5001

WORKDIR /qmk_api
COPY . /qmk_api
RUN pip3 install -r requirements.txt git+https://github.com/qmk/qmk_compiler.git@master git+https://github.com/skullydazed/kle2xy.git@master
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
CMD ./run
