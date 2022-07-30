FROM fedora:34

#MAINTAINER Rafael Lins "leafarlins@gmail.com"

RUN dnf update -y && \
    dnf install -y python3-3.9.13 python-pip && \
    dnf clean all && rm -rf /var/cache/yum

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

#RUN env/bin/activate && \
RUN pip install -r requirements.txt

COPY app /app

ENTRYPOINT [ "flask" ]

CMD [ "run", "--host=0.0.0.0" ]
