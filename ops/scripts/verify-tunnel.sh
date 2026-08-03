#!/usr/bin/env sh
# =============================================================================
# SBOZOR — SC#5 ning 3-DA'VOSI: marshrut haqiqatan tunneldan ketadi.
#
# ⚠⚠ BU SKRIPT CI'DA ISHLAMAYDI VA ISHLASHI HAM KERAK EMAS.
#
# CI konteynerida `wg0` interfeysi umuman yo'q. Ya'ni bu yerdagi
# tekshiruvni CI'ga qo'shish IKKI xil yomon natijaga olib kelardi:
#
#   * «tunnel yo'q -> test o'tdi» deb yozilsa, u HAR DOIM yashil bo'lardi
#     va HECH NIMA isbotlamasdi — Pitfall 10 ning aynan o'zi: «tunnelni
#     o'chir, ulanish uzilishini ko'r» testi tunnel BO'LMAGAN muhitda
#     har doim muvaffaqiyatli «uziladi»;
#   * «tunnel yo'q -> test yiqildi» deb yozilsa, CI doim qizil bo'lardi.
#
# Shuning uchun SC#5 UCHTA da'voga ajratilgan (`ops/wireguard/README.md`
# §5). Ikkitasi CI'da o'lchanadi:
#
#   1-da'vo  tests/unit/test_nvr_host_validation.py   (xususiy manzil)
#   2-da'vo  tests/unit/test_wireguard_config.py      (AllowedIPs)
#   3-da'vo  ← SHU SKRIPT                             (deploy smoke-testi)
#
# U go-live checklist'ining bandi: VPS'da, deploy'dan KEYIN, bir marta.
# =============================================================================
#
# Ishlatilishi:
#     ops/scripts/verify-tunnel.sh 192.168.1.64
#     ops/scripts/verify-tunnel.sh 192.168.1.64 wg0
#
# Chiqish kodi: 0 — marshrut tunneldan ketadi; 1 — ketmaydi yoki
# tekshirib bo'lmadi. Nol bo'lmagan kod deploy'ni TO'XTATISHI kerak.

set -eu

NVR_IP="${1:-}"
WG_IFACE="${2:-wg0}"

if [ -z "$NVR_IP" ]; then
    echo "ISHLATILISHI: $0 <nvr-ip> [wg-interfeysi]" >&2
    echo "Masalan:      $0 192.168.1.64 wg0" >&2
    exit 1
fi

if ! command -v ip >/dev/null 2>&1; then
    echo "XATO: \`ip\` buyrug'i topilmadi (iproute2 o'rnatilmagan)." >&2
    echo "      Bu skript LINUX VPS uchun — dev xostda ishlatilmaydi." >&2
    exit 1
fi

# ⚠ INTERFEYSNING MAVJUDLIGI ALOHIDA TEKSHIRILADI.
#   Usiz `ip route get` marshrutni standart shlyuz orqali qaytarardi va
#   xato «marshrut noto'g'ri» bo'lib ko'rinardi — aslida esa tunnel
#   umuman ko'tarilmagan bo'lardi. Ikki xil nosozlik, ikki xil tuzatish.
if ! ip link show "$WG_IFACE" >/dev/null 2>&1; then
    echo "XATO: \`$WG_IFACE\` interfeysi YO'Q — tunnel ko'tarilmagan." >&2
    echo "      Tekshiring: systemctl status wg-quick@$WG_IFACE" >&2
    exit 1
fi

ROUTE="$(ip route get "$NVR_IP" 2>/dev/null || true)"

if [ -z "$ROUTE" ]; then
    echo "XATO: \`ip route get $NVR_IP\` marshrut qaytarmadi." >&2
    exit 1
fi

# `ip route get 192.168.1.64` chiqishi:
#     192.168.1.64 dev wg0 src 10.10.0.1 uid 0
#                  ^^^^^^^ — aynan shu qism tekshiriladi
case "$ROUTE" in
    *"dev $WG_IFACE"*)
        echo "OK: $NVR_IP -> \`$WG_IFACE\` (tunnel)"
        echo "    $ROUTE"
        exit 0
        ;;
esac

echo "XATO: $NVR_IP marshruti \`$WG_IFACE\` ORQALI EMAS." >&2
echo "      $ROUTE" >&2
echo "" >&2
echo "  Ehtimoliy sabablar:" >&2
echo "   * peer'ning \`AllowedIPs\` ida bu subnet yo'q" >&2
echo "     (\`wg show $WG_IFACE allowed-ips\` bilan tekshiring);" >&2
echo "   * xostda bu subnet uchun aniqroq (ko'proq mos) marshrut bor;" >&2
echo "   * NVR manzili noto'g'ri kiritilgan." >&2
exit 1
