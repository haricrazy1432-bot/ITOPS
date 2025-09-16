FROM python:3.11-slim
WORKDIR /app
COPY app.py .
COPY rundeck_client.py .
RUN pip install aiohttp aiosqlite requests python-dotenv botbuilder-core botbuilder-schema botbuilder-integration-aiohttp
CMD ["python", "app.py"]
