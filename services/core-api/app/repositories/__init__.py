"""DB kirish qatlami.

Ikki xil repozitoriy bo'ladi va ular ATAYIN aralashtirilmaydi:

* **tenant-scoped** — `sbozor_core.tenancy.TenantScopedRepository` dan meros
  oladi, `app.market_id` GUC'i o'rnatilgan sessiyada ishlaydi va har
  `select()` ni `scoped()` dan o'tkazadi (2-qatlam filtri);
* **`auth_repo`** — tenant kontekstisiz ishlaydigan YAGONA repozitoriy.
  Login va sessiya yo'li `SECURITY DEFINER` funksiyalari orqali o'tadi,
  chunki o'sha paytda bozor hali noma'lum (RESEARCH Pitfall 3).
"""
