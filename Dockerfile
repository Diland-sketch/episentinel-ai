FROM python:3.13.4-slim-bookworm@sha256:9ed09f78253eb4f029f3d99e07c064f138a6f1394932c3807b3d0738a674d33b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src:/app \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /app
COPY deploy/requirements.lock /app/deploy/requirements.lock
RUN pip install --no-cache-dir -r deploy/requirements.lock
COPY src/episentinel /app/src/episentinel
COPY api /app/api
COPY app/retrospective.py /app/app/retrospective.py
COPY scripts/run_retrospective.py /app/scripts/run_retrospective.py
COPY scripts/profile_render.py /app/scripts/profile_render.py
COPY deploy /app/deploy
COPY docs/experiments /app/docs/experiments
COPY docs/benchmarks /app/docs/benchmarks
RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /app
USER 10001
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','10000')+'/api/v1/ready',timeout=4)"
CMD ["python", "-m", "deploy.start"]
