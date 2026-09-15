#!/usr/bin/env python3
"""
CS2/CS:GO skin narxlarini solishtiruvchi Telegram bot.

Ishlash printsipi:
1. Telegram'dan botga yozilgan YANGI xabarlarni oladi (getUpdates orqali,
   "offset" fayl orqali qaysi xabarlargacha o'qilganini eslab qoladi).
2. Har bir xabarni tekshiradi:
   - Agar Steam Community Market havolasi bo'lsa, undan skin nomini ajratadi
   - Aks holda, butun xabar matnini skin nomi (masalan
     "AK-47 | Redline (Field-Tested)") deb qabul qiladi
3. Skin narxini ikkita bozordan oladi:
   - Steam Community Market (rasmiy, komissiya yuqoriroq)
   - Skinport (uchinchi tomon bozori, odatda arzonroq)
4. Ikkalasini solishtirib, qaysi biri arzonroq ekanini javob qilib yuboradi.

Ishga tushirish:
    python3 skin_price_bot.py

Muhit o'zgaruvchilari:
    TELEGRAM_BOT_TOKEN - @BotFather bergan ushbu botning tokeni (MAJBURIY)
    CURRENCY           - (ixtiyoriy) standart: USD
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CURRENCY = os.environ.get("CURRENCY", "USD")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OFFSET_FILE = os.path.join(SCRIPT_DIR, "offset.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Steam valyuta kodlari (priceoverview API uchun)
STEAM_CURRENCY_CODES = {"USD": 1, "EUR": 3, "RUB": 5, "GBP": 2}

# Referal havolalar — narxi tekshirilmaydi (bu saytlarning ochiq narx API'si
# yo'q), lekin har bir javobga qo'shimcha xarid variantlari sifatida
# qo'shiladi, shunday qilib referal kredit ishlab turadi.
REFERRAL_LINKS = [
    ("LIS-skins", "https://lis-skins.com/?rf=1708521"),
    ("Aim.market", "https://aim.market/p/bf44ace0-3c48-44f0-9b73-5f988556afe7"),
]


def http_get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_offset():
    if not os.path.exists(OFFSET_FILE):
        return 0
    try:
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("offset", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def save_offset(offset):
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


def get_updates(offset):
    url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        f"?offset={offset}&timeout=0&allowed_updates=[\"message\"]"
    )
    data = http_get_json(url)
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates xatosi: {data}")
    return data["result"]


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        print(f"sendMessage xatosi: {result}", file=sys.stderr)


def extract_market_hash_name(text):
    """Xabar matnidan skin nomini ajratadi: Steam Market havolasi bo'lsa
    undan, aks holda butun matnni skin nomi deb qabul qiladi."""
    text = text.strip()
    if "steamcommunity.com/market/listings/" in text:
        parsed = urllib.parse.urlparse(text)
        segments = [s for s in parsed.path.split("/") if s]
        # .../market/listings/{appid}/{market_hash_name}
        if len(segments) >= 4:
            return urllib.parse.unquote(segments[-1])
    return text


def get_steam_price(market_hash_name):
    currency_code = STEAM_CURRENCY_CODES.get(CURRENCY, 1)
    params = urllib.parse.urlencode(
        {
            "appid": 730,  # CS2/CS:GO
            "currency": currency_code,
            "market_hash_name": market_hash_name,
        }
    )
    url = f"https://steamcommunity.com/market/priceoverview/?{params}"
    try:
        data = http_get_json(url)
        if not data.get("success"):
            return None
        price_str = data.get("lowest_price") or data.get("median_price")
        if not price_str:
            return None
        return {
            "market": "Steam Community Market",
            "price_display": price_str,
            "url": (
                "https://steamcommunity.com/market/listings/730/"
                + urllib.parse.quote(market_hash_name)
            ),
        }
    except Exception as exc:
        print(f"Steam narxini olishda xatolik: {exc}", file=sys.stderr)
        return None


def get_skinport_price(market_hash_name):
    params = urllib.parse.urlencode(
        {"app_id": 730, "currency": CURRENCY, "tradable": "false"}
    )
    url = f"https://api.skinport.com/v1/items?{params}"
    try:
        items = http_get_json(url)
    except Exception as exc:
        print(f"Skinport'dan ro'yxatni olishda xatolik: {exc}", file=sys.stderr)
        return None

    target = market_hash_name.strip().lower()
    for item in items:
        if item.get("market_hash_name", "").strip().lower() == target:
            price = item.get("min_price")
            if price is None:
                return None
            return {
                "market": "Skinport",
                "price_display": f"{price} {CURRENCY}",
                "url": item.get("item_page")
                or f"https://skinport.com/item/{urllib.parse.quote(market_hash_name)}",
            }
    return None


def parse_price_number(price_display):
    """'$12.34' yoki '12.34 USD' kabi matndan raqamni ajratadi, solishtirish
    uchun. Ajratib bo'lmasa None qaytaradi."""
    digits = "".join(c for c in price_display if c.isdigit() or c in ".,")
    digits = digits.replace(",", "")
    try:
        return float(digits)
    except ValueError:
        return None


def build_reply(market_hash_name, results):
    referral_lines = ["\n🛒 Boshqa xarid variantlari:"] + [
        f'• <a href="{html_escape(url, True)}">{html_escape(name)}</a>'
        for name, url in REFERRAL_LINKS
    ]

    if not results:
        not_found = (
            f"❌ \"{html_escape(market_hash_name)}\" uchun hech qanday bozorda "
            "narx topilmadi. Nomni to'g'ri yozganingizga ishonch hosil qiling "
            "(masalan: <code>AK-47 | Redline (Field-Tested)</code>) yoki "
            "Steam Market havolasini yuboring."
        )
        return "\n".join([not_found] + referral_lines)

    # Eng arzonini topish
    priced = [
        (r, parse_price_number(r["price_display"]))
        for r in results
        if parse_price_number(r["price_display"]) is not None
    ]
    cheapest = min(priced, key=lambda pair: pair[1])[0] if priced else None

    lines = [f"🔍 <b>{html_escape(market_hash_name)}</b>\n"]
    for r in results:
        marker = "✅ " if cheapest and r["market"] == cheapest["market"] else "• "
        lines.append(
            f'{marker}<a href="{html_escape(r["url"], True)}">{html_escape(r["market"])}</a>: '
            f'<b>{html_escape(r["price_display"])}</b>'
        )

    if cheapest:
        lines.append(f"\n💰 Eng arzoni: <b>{html_escape(cheapest['market'])}</b>")

    lines.extend(referral_lines)

    return "\n".join(lines)


def html_escape(text, quote=False):
    import html as _html

    return _html.escape(text, quote=quote)


TRIGGER_PHRASES = ("skin narx", "skin narxi", "skin narxlari", "/skin")


def extract_group_query(text):
    """Guruh chatida faqat trigger so'z bilan boshlangan xabarlarga javob
    beriladi. Trigger topilsa, undan keyingi qismni (skin nomini) qaytaradi
    (bo'sh bo'lishi ham mumkin — shunda foydalanuvchidan nom so'raladi)."""
    lowered = text.strip().lower()
    for trigger in TRIGGER_PHRASES:
        if lowered.startswith(trigger):
            rest = text.strip()[len(trigger):].strip(" :-—")
            return rest
    return None


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    text = message.get("text", "")
    if not chat_id or not text:
        return

    if text.strip().startswith("/start"):
        send_message(
            chat_id,
            "👋 Salom! Menga skin nomini (masalan "
            "<code>AK-47 | Redline (Field-Tested)</code>) yoki Steam Market "
            "havolasini yuboring — men Steam va Skinport narxlarini "
            "solishtirib beraman.",
        )
        return

    if chat_type in ("group", "supergroup"):
        # Guruhda spam bo'lmasligi uchun faqat trigger so'z bilan
        # boshlangan xabarlarga javob beriladi
        query = extract_group_query(text)
        if query is None:
            return  # trigger yo'q — bu xabar bizga tegishli emas
        if not query:
            send_message(
                chat_id,
                "🔍 Qaysi skin narxini bilmoqchisiz? Masalan:\n"
                "<code>skin narxi: AK-47 | Redline (Field-Tested)</code>",
            )
            return
        market_hash_name = extract_market_hash_name(query)
    else:
        market_hash_name = extract_market_hash_name(text)

    results = []
    steam_price = get_steam_price(market_hash_name)
    if steam_price:
        results.append(steam_price)
    skinport_price = get_skinport_price(market_hash_name)
    if skinport_price:
        results.append(skinport_price)

    reply = build_reply(market_hash_name, results)
    send_message(chat_id, reply)


def main():
    if not BOT_TOKEN:
        print(
            "XATOLIK: TELEGRAM_BOT_TOKEN muhit o'zgaruvchisini o'rnating.",
            file=sys.stderr,
        )
        sys.exit(1)

    offset = load_offset()
    try:
        updates = get_updates(offset)
    except Exception as exc:
        print(f"Yangilanishlarni olishda xatolik: {exc}", file=sys.stderr)
        sys.exit(1)

    if not updates:
        print("Yangi xabar yo'q.")
        return

    max_update_id = offset
    for update in updates:
        max_update_id = max(max_update_id, update["update_id"] + 1)
        message = update.get("message")
        if message:
            try:
                handle_message(message)
            except Exception as exc:
                print(f"Xabarni qayta ishlashda xatolik: {exc}", file=sys.stderr)

    save_offset(max_update_id)
    print(f"{len(updates)} ta xabar qayta ishlandi.")


if __name__ == "__main__":
    main()
