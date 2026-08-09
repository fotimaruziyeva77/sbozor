"""`cv-service` ning baza yozuvchilari.

Bugun bu yerda AYNAN BITTA modul bor — `occupancy_writer.py`. `cv-service`
bazaga UCH marta tegadi va uchalasi ham tor: kadr qatorini o'qish, faol
zonalarni o'qish (ikkalasi `jobs/detect.py` da, chunki ular ORKESTRATSIYA
qadamlari) va bandlik hodisalarini yozish (shu yerda).

⚠ REPOZITORIY QATLAMI `core-api` DAN NUSXA OLINMADI. `TenantScopedRepository`
  (`sbozor_core.tenancy`) ikkinchi qatlam filtrini beradi va u shu yerda
  ham ishlatiladi — lekin `core-api` ning repozitoriylari o'nlab metodli
  domen yuzalari, bu servisda esa YOZISHDAN boshqa hech nima yo'q.
"""
