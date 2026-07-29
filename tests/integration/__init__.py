"""Integratsiya testlari — DB xulq-atvori (FOUND-03, FOUND-05).

`tests/tenancy` dan farqi: u yerda SXEMA INVARIANTLARI tekshiriladi
(`pg_catalog` dan o'qib "policy bormi, FORCE qo'yilganmi"), bu yerda esa
JADVALLARNING AMALDAGI XULQI — haqiqiy INSERT/UPDATE/DELETE qilinadi va
natijasi o'lchanadi.

Ikkalasi ham kerak: invariant "mexanizm o'rnatilgan" deydi, integratsiya
testi esa "mexanizm ishlaydi" deydi. Birinchisisiz ikkinchisi yangi jadvalni
qamramaydi; ikkinchisisiz birinchisi noto'g'ri yozilgan trigger tanasini
ko'rmaydi.

Barcha testlar HAQIQIY `postgres:18.4-trixie` konteyneriga qarshi ishlaydi
va izolyatsiya da'volari HAR DOIM `sbozor_app` roli bilan olinadi.
"""
