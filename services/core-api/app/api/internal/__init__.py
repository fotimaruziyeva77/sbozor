"""ICHKI marshrutlar — foydalanuvchi emas, INFRASTRUKTURA chaqiradi.

`app/api/v1/` DAN ATAYIN AJRATILGAN paket. Farq bitta jumlada:
`v1` — mahsulotning ommaviy kontrakti (versiyalanadi, OpenAPI'da
hujjatlashtiriladi, `Bearer` token bilan chaqiriladi); bu yerdagi
marshrutlarni esa nginx o'z subso'rovi bilan chaqiradi va ular
imzolangan CHIPTAGA tayanadi.

Ajratish kod tashkilotining qulayligi emas, TASNIF: `v1` ostidagi har
bir marshrut avtomatik ravishda cross-tenant matritsasiga tushadi va
undan 401/404 xulqi kutiladi. Bu yerdagi marshrutlar boshqa
kontraktda (403/204) ishlaydi va ular o'z testlariga ega bo'lishi
SHART — matritsadan chiqarilishi `tests/tenancy/test_cross_tenant.py::
EXEMPT_ROUTES` da SABAB bilan yozilgan.
"""
