"""Alert supurgisi OPS CHATI sozlanmagan bo'lsa ham ISHLAYDI.

=============================================================================
⛔⛔ BU NOSOZLIK JONLI TIZIMDA O'LCHANDI (260902), TAXMIN QILINMAGAN.

`worker.py::alert_sweep_task` ning birinchi qatori shunday edi:

    if not state.alerts_enabled:
        return

`Settings.alerts_enabled` = `bool(token AND chat_id)`. Ishlab chiqarish
serverida `TELEGRAM_BOT_TOKEN` to'ldirilgan, `TELEGRAM_CHAT_ID` esa BO'SH
edi — ya'ni supurgi har besh daqiqada ishga tushib, birinchi qatorda
qaytardi. Jurnalda `Executing task alert.sweep` ko'rinardi, natija esa
hech qayerda yo'q edi.

O'lchangan oqibat:

  * `alert_events` jadvalida NOL qator (12 kun davomida);
  * `system_heartbeats` da `alert_sweep` komponenti UMUMAN yo'q;
  * `backup` konteyneri 12 kun `backup_unconfigured` deb qaytarardi va
    bitta ham zaxira olinmagan edi;
  * `backup_stale` — CRITICAL va `never_suppressed` — HECH QACHON
    ko'tarilmadi.

Ya'ni kuzatuv qatlami butunlay Telegram sozlamasiga bog'lanib qolgan edi:
ops chati yo'q bozorda tizim o'z nosozliklarini KO'RMASDI ham.

⚠ YUBORISH BILAN YOZISH BOG'LIQ EMAS va `_notify` buni allaqachon
  to'g'ri qiladi: Telegram yiqilsa `alert_events` qatori BARIBIR yoziladi
  va `notified_at` `NULL` bo'lib qoladi — UI aynan shu holatni
  «xabar yuborilmadi» deb ko'rsatadi. Demak manzilsiz supurgi
  ma'nosiz emas: u panelga ko'rinadigan yozuvni yaratadi.
"""

from __future__ import annotations

import inspect


class TestSupurgiOpsChatsizIshlaydi:
    def test_erta_qaytish_yoq(self) -> None:
        """⛔ ASOSIY O'LCHOV: `alerts_enabled` supurgini TO'XTATMAYDI.

        Manba matnida tekshiriladi, chunki `alert_sweep_task` — taskiq
        qobig'i: uni chaqirish uchun butun broker holatini qurish kerak
        bo'lardi va test o'lchamoqchi bo'lgan da'vo («shu shartda
        `return` yo'q») o'sha qurilmaning ortida ko'rinmay ketardi.
        """
        from app import worker

        manba = inspect.getsource(worker.alert_sweep_task)
        tana = manba.split('"""')[-1]

        # ⚠ IZOHLAR HISOBGA OLINMAYDI: `return` so'zi shu blokdagi
        #   izohda ham uchraydi (nima o'zgarganini tushuntiradi) va uni
        #   kod deb sanash testni yolg'on qizartirardi.
        kod = [q for q in tana.splitlines() if not q.strip().startswith("#")]
        tana = chr(10).join(kod)

        assert "await alert_sweep(" in tana, "supurgi umuman chaqirilmayapti"

        i_shart = tana.find("if not state.alerts_enabled:")
        i_chaqiruv = tana.find("await alert_sweep(")
        assert i_shart != -1, "sozlama tekshiruvi butunlay yo'qolgan — sabab jurnalga yozilmaydi"
        assert i_shart < i_chaqiruv, "tekshiruv chaqiruvdan keyin"

        oraliq = tana[i_shart:i_chaqiruv]
        assert "return" not in oraliq, (
            "ops chati yo'q bo'lsa supurgi qaytib ketyapti — 260902 dagi "
            "«lar 12 kun zaxirasiz, bitta ham alert yo'q» holati qaytdi"
        )

    def test_sabab_jurnalga_yoziladi(self) -> None:
        """⚠ JIM O'TMAYDI: ops chati yo'qligi jurnalda ko'rinsin — aks
        holda «alertlar yozilyapti, lekin hech kimga bormayapti»
        holati yana ko'rinmas bo'lardi."""
        from app import worker

        tana = inspect.getsource(worker.alert_sweep_task).split('"""')[-1]
        assert "log.info(" in tana or "log.warning(" in tana, (
            "ops chati yo'qligi hech qayerda qayd etilmayapti"
        )
