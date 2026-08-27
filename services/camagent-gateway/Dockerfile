# CamAgent gateway — tunnelsiz bozorlardagi agentlarning kirish nuqtasi.
#
# Bu SBOZOR "3 servis" cheklovidagi servis EMAS: u boshqa repoda
# (CamAgent) yashaydigan, shu yerga vendoring qilingan tayyor komponent —
# `db`/`cache`/`storage` bilan bir toifada. Ichi: FastAPI + SQLite (WAL)
# + S3 mijozi. Rasm S3'ga (`camagent/` prefiksi), metadata SQLite'ga
# (`/data` volume) yoziladi.
FROM python:3.13-slim

# Bytecode kesh konteyner qatlamini shishirmasin; jurnallar real vaqtda
# ko'rinsin (uvicorn stdout orqali).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY agent_gateway ./agent_gateway

# Konteynerda tashqariga compose tarmog'i orqali xizmat qilinadi —
# 0.0.0.0 shu yerda beriladi, kodda emas (kodning standarti 127.0.0.1
# bo'lib qoladi — lokal dev xavfsizligi).
ENV CAMAGENT_GW_HOST=0.0.0.0 \
    CAMAGENT_GW_PORT=8787 \
    CAMAGENT_GW_DATA=/data

VOLUME /data
EXPOSE 8787

CMD ["python", "-m", "agent_gateway"]
