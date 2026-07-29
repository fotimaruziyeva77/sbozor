"""Alembic migratsiya paketi.

`__init__.py` ATAYIN mavjud: migratsiya fayllari va `env.py`
`from migrations.helpers import ...` shaklida import qiladi, ya'ni `migrations`
haqiqiy paket bo'lishi kerak (namespace paket mypy'da modul nomlarini
chalkashtiradi). Repo ildizi `alembic.ini` dagi `prepend_sys_path = .` orqali
`sys.path` ga qo'shiladi.
"""

from __future__ import annotations
