FROM python:3.11-slim
WORKDIR /app
COPY server.py .
COPY servicenow_client.py .
RUN pip install flask requests python-dotenv
CMD ["python", "server.py"]
