FROM python:3.9
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY main.py main.py
COPY sql.py sql.py
COPY config/config.py config/config.py
CMD ["python3", "main.py"]