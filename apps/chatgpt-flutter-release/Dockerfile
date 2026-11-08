# Build from the repository root so the shared scripts are included:
#   docker build -f apps/chatgpt-flutter-release/Dockerfile -t flutter-release-check .
FROM python:3.13-slim

WORKDIR /srv
COPY apps/chatgpt-flutter-release/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/permission_audit.py scripts/bump_version.py scripts/
COPY apps/chatgpt-flutter-release/server.py apps/chatgpt-flutter-release/

RUN useradd --create-home --uid 10001 app
USER app

ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000
WORKDIR /srv/apps/chatgpt-flutter-release
CMD ["sh", "-c", "exec uvicorn server:app --host \"$HOST\" --port \"$PORT\" --no-access-log"]
