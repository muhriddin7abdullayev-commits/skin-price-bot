# CS2 Skin narxlarini solishtiruvchi bot

Botga skin nomini yoki Steam Market havolasini yuborsangiz, u **Steam
Community Market** va **Skinport** narxlarini solishtirib, qaysi biri
arzonroq ekanini aytib beradi.

## Qanday ishlaydi

- Har 5 daqiqada GitHub Actions orqali botga yozilgan yangi xabarlarni
  tekshiradi (`offset.json` orqali qaysi xabarlargacha o'qilganini eslab
  qoladi, shunday qilib bir xabarga ikki marta javob bermaydi)
- Yangi xabar topsa:
  - Agar bu Steam Market havolasi bo'lsa, undan skin nomini ajratadi
  - Aks holda, butun matnni skin nomi deb qabul qiladi
  - Ikkala bozordan narxni so'raydi va solishtirib javob yozadi

**Eslatma**: Javob 1-5 daqiqagacha kechikishi mumkin (GitHub'ning tekshirish
oralig'i tufayli) — bu darhol javob beradigan bot emas, lekin butunlay bepul.

## O'rnatish

### 1-qadam: @BotFather orqali bot (allaqachon qilingan bo'lsa, o'tkazib
yuboring)

### 2-qadam: Fayllarni GitHub repo'siga yuklash

Bu papkadagi barcha fayllarni (`skin_price_bot.py`, `offset.json`,
`.github/workflows/skin_price_bot.yml`, `README.md`) yangi (yoki mavjud)
GitHub repo'siga yuklang — avvalgi HLTV botini sozlaganingizdagi kabi
("uploading an existing file" orqali).

### 3-qadam: Secret qo'shish

Repo → **Settings → Secrets and variables → Actions → New repository
secret**:

- Nomi: `SKIN_BOT_TOKEN`
- Qiymati: shu botning (`@bingo_skincheck_bot`) tokeni

⚠️ **Muhim**: bu nom avvalgi yangiliklar botidagi `TELEGRAM_BOT_TOKEN`dan
**boshqacha** — chunki bu boshqa, alohida bot. Agar ikkalasini bitta repo'da
saqlasangiz, ikkita turli nomdagi secret kerak bo'ladi.

### 4-qadam: Sinab ko'rish

1. Repo → **Actions** → "Skin narxlarini tekshirish boti" → **Run
   workflow** bilan birinchi marta qo'lda ishga tushiring
2. Telegram'da botingizga (`@bingo_skincheck_bot`) yozing:
   ```
   AK-47 | Redline (Field-Tested)
   ```
   yoki Steam Market havolasini yuboring
3. Bir necha daqiqadan keyin (yoki workflow'ni yana "Run workflow" bilan
   qo'lda ishga tushirsangiz — darhol) bot javob beradi

## Muhim eslatmalar

- Skin nomini **aniq** yozish kerak (katta-kichik harf muhim emas, lekin
  so'zlar va belgilar — `|`, qavslar — to'g'ri bo'lishi kerak). Eng ishonchli
  yo'l — Steam Market'dagi skin sahifasining havolasini to'g'ridan-to'g'ri
  yuborish.
- Skinport narxi topilmasa (masalan, o'sha skin ularda yo'q bo'lsa), faqat
  Steam narxi ko'rsatiladi.
- Kelajakda boshqa bozorlarni (masalan CSFloat, BitSkins, DMarket) qo'shish
  ham mumkin — ular uchun ko'pincha API kalit kerak bo'ladi.
