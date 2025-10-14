FROM python:3.9-slim

WORKDIR /app

RUN pip install prometheus-client==0.17.1

COPY ml_simulator.py .

EXPOSE 9500

CMD ["python", "ml_simulator.py"]
