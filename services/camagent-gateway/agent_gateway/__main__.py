"""Gateway server: python -m agent_gateway [--port 8787] [--data DIR]

Dev: ishga tushgach http://127.0.0.1:8787/admin da panel ochiladi,
birinchi ishga tushishda KARMANA-TEST aktivatsiya kodi yaratiladi.

Ishlab chiqarish (Docker/sbozor): hamma narsa muhitdan sozlanadi —
bayroqlar berilmasa quyidagi o'zgaruvchilar o'qiladi:

    CAMAGENT_GW_HOST          tinglash manzili (standart 127.0.0.1;
                              konteynerda 0.0.0.0 beriladi)
    CAMAGENT_GW_PORT          port (standart 8787)
    CAMAGENT_GW_DATA          ma'lumot papkasi (gateway.db, media, disk rasmlar)
    CAMAGENT_GW_ADMIN_TOKEN   panel kaliti (bo'sh bo'lsa tasodifiy yaratiladi
                              va konsolga chiqariladi)
    CAMAGENT_GW_NO_BOOTSTRAP  "1" bo'lsa KARMANA-TEST sinov kodi YARATILMAYDI
                              (ishlab chiqarishda majburiy — oldindan ma'lum
                              kod ochiq turmasin)
    CAMAGENT_GW_S3_BUCKET     berilsa rasmlar S3-mos omborga yoziladi
    CAMAGENT_GW_S3_ENDPOINT   masalan http://storage:8333 (SeaweedFS)
    CAMAGENT_GW_S3_ACCESS_KEY / CAMAGENT_GW_S3_SECRET_KEY / CAMAGENT_GW_S3_REGION
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from .app import build_app
from .storage import storage_from_env


def main() -> None:
    env = os.environ.get
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int,
                        default=int(env("CAMAGENT_GW_PORT", "8787")))
    parser.add_argument("--host", default=env("CAMAGENT_GW_HOST", "127.0.0.1"))
    parser.add_argument("--data", default=env("CAMAGENT_GW_DATA", "server_data"))
    parser.add_argument("--admin-token", default=env("CAMAGENT_GW_ADMIN_TOKEN", ""),
                        help="panel kaliti (bo'sh bo'lsa tasodifiy yaratiladi)")
    args = parser.parse_args()

    data_dir = Path(args.data)
    app = build_app(data_dir, storage=storage_from_env(data_dir),
                    admin_token=args.admin_token or None)
    gw = app.state.gateway
    bootstrap_ochiq = env("CAMAGENT_GW_NO_BOOTSTRAP", "") != "1"
    if bootstrap_ochiq and not gw.db.list_codes():
        code = gw.db.create_code("Karmana bozori (sinov)", "karmana-01", code="KARMANA-TEST")
        print(f"[gateway] aktivatsiya kodi yaratildi: {code}", flush=True)
    # Panel kalit bilan himoyalangan: undan agentlarga buyruq yuboriladi.
    #
    # `flush=True` MAJBURIY: chiqish faylga yoki quvurga yo'naltirilganda
    # Python stdout'ni buferlaydi, uvicorn esa abadiy ishlaydi — bufer
    # hech qachon bo'shamaydi va havola HECH QAYERGA chiqmaydi.
    # Panel esa "konsolga chiqarilgan havolani oching" deb turadi.
    print("[gateway] admin panel — kalit havola ICHIDA, shuni oching:",
          flush=True)
    print(f"          http://{args.host}:{args.port}/admin?token={gw.admin_token}",
          flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
