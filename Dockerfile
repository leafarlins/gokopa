FROM fedora:31

MAINTAINER Rafael Lins "leafarlins@gmail.com"

RUN dnf update -y && \
    dnf clean all && rm -rf /var/cache/yum

RUN dnf install -y python3-3.7.6 python-pip && \
    dnf clean all && rm -rf /var/cache/yum

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

#RUN env/bin/activate && \
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]
