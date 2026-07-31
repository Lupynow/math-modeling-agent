FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY pyproject.toml /tmp/modeling-agent/
COPY src /tmp/modeling-agent/src
RUN pip install --no-cache-dir /tmp/modeling-agent

COPY knowledge/math-modeling-skills/skills /workspace/knowledge/math-modeling-skills/skills

EXPOSE 8000

CMD ["uvicorn", "modeling_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
