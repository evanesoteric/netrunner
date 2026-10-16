FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
# Frontend changes also define a new development build.
COPY frontend /build-input/frontend
ARG NETRUNNER_BUILD_NONCE=""
RUN python -c "import hashlib,pathlib,os; h=hashlib.sha256(); paths=sorted([*pathlib.Path('backend').rglob('*'), *pathlib.Path('/build-input').rglob('*'), pathlib.Path('requirements.txt')]); [(h.update(str(p).encode()), h.update(p.read_bytes())) for p in paths if p.is_file()]; h.update(os.environ.get('NETRUNNER_BUILD_NONCE','').encode()); pathlib.Path('/app/build-id').write_text(h.hexdigest())"
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
