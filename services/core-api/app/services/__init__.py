"""Domen servislari — routerdan HAM, repozitoriydan HAM mustaqil qatlam.

NEGA ALOHIDA PAKET (`repositories/` ga qo'shilmadi): bu moduldagi kod DB
ga umuman tegmaydi. `xlsx_reader` bayt massivini o'qiydi, `xlsx_template`
bayt massivi yozadi, `import_validator` esa tayyor lug'atlar ustida sof
funksiya sifatida ishlaydi. Uchalasini repozitoriy paketiga qo'yish
"repozitoriy = DB yuzasi" degan konvensiyani jimgina buzardi va keyingi
o'quvchi bu fayllarda `SELECT` qidirardi.

Uchalasi ham SESSIYASIZ va SINXRON — ya'ni ularni unit test bilan
(konteynersiz, migratsiyasiz) to'liq qamrash mumkin va aynan shuning
uchun hujum testlari `tests/unit/` da yashaydi.
"""

from __future__ import annotations

__all__: list[str] = []
