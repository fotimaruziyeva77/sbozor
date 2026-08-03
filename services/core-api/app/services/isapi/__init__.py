"""Hikvision ISAPI qatlami — xato taksonomiyasi, parser, klient va kashfiyot.

Loyihaning BIRINCHI chiquvchi HTTP integratsiyasi (`03-PATTERNS.md` §4.2:
`httpx` `services/` va `packages/` ichida nol marta import qilingan edi —
uni ishlatadigan 24 fayl hammasi `tests/` ichida edi).

Qatlamlar va ularning chegaralari:

    errors.py     sof reyestr    — kodlar va istisno; hech kimga bog'liq emas
    parser.py     sof transform  — baytdan dataclass'ga; tarmoqni bilmaydi
    client.py     I/O            — Digest, timeout, retry, xatoga xaritalash
    discovery.py  orkestratsiya  — klient + repozitoriy; navbatni BILMAYDI

Yo'nalish bir tomonlama: `discovery` -> `client` -> `parser` -> `errors`.
Teskari import yo'q va bo'lmasligi kerak — parser klientni bilsa uni
tarmoqsiz sinab bo'lmasdi.
"""

from __future__ import annotations
