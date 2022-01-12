FROM python:3

COPY requirements.txt ./

RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /opt/project
WORKDIR /opt/project/src
