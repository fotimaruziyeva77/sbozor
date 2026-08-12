"""SBOZOR bot-service — sotuvchi va direktor Telegram botlari.

⛔ Bu paket `core-api` va `cv-service` dagi `app` paketlari bilan BIR XIL
   NOMDA, lekin ular UCH XIL image'da yashaydi va hech qachon bitta
   `sys.path` ga tushmaydi. Bu chalkashlikning oqibati `tests/unit/
   test_sentry_processes.py:63-98` da o'lchangan: root darvoza `cv-service`
   uchun `importlib.import_module("app.worker")` chaqirsa, u JIMGINA
   `core-api` ning modulini qaytargan bo'lardi. Shuning uchun begona kod
   bazasi root darvozada MANBA darajasida, obyekt darajasida esa O'Z
   konteynerida (`bot-tests`) o'lchanadi.
"""
