FROM python:3

WORKDIR /checklinks

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY checklinks /checklinks
COPY tests /tests

