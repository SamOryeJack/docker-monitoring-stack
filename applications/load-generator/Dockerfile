FROM python:3.9-slim

WORKDIR /app

RUN pip install requests

COPY load_generator.py .

CMD ["python", "load_generator.py"]
