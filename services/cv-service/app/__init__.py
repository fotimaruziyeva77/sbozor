"""`cv-service` — SBOZOR ning UCHINCHI servisi (D-23).

Bu paket `services/core-api/app` bilan NOMDOSH va ular BOSHQA image'larda
yashaydi: har birining o'z `pyproject.toml`, `uv.lock` va `Dockerfile` i bor
(W0-2). Nomdoshlikning bitta o'lchangan oqibati bor va u
`tests/unit/test_sentry_processes.py` da yozilgan: root `tests` konteyneri
faqat `core-api` ning `app` ini import qila oladi, ya'ni bu paketning
darvozalari O'Z konteynerida (`cv-tests`) yuradi.
"""
