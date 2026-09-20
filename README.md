# System-wide English Writing & Learning Companion
## دستیار سراسری بیان و تقویت نگارش انگلیسی

این مخزن شامل مستندات جامع محصول، تصمیمات معماری، سوابق تحلیل نیازمندی‌ها، و نمونه اولیه (Prototype) تست‌شده برای **دستیار سراسری بیان و یادگیری نگارش انگلیسی** است.

---

## 🎯 هویت و مأموریت محصول
این محصول یک «گرامر چکر معمولی» نیست؛ بلکه یک **لایه‌ی تعاملی سراسری (System-wide) روی سیستم‌عامل** است که به کاربر اجازه می‌دهد حتی با انگلیسی شکسته یا با ساختار ذهنی فارسی بنویسد؛ سیستم فوراً:
1. نیت فنی کاربر را درک کرده و به انگلیسی روان، طبیعی و حرفه‌ای تبدیل می‌کند.
2. **برداشت خود از منظور کاربر را به زبان فارسی نمایش می‌دهد (Semantic Checkpoint)** تا از بروز خطای *Semantic Drift* در پرامپت‌ها و کدها جلوگیری شود.
3. در یک پنجره شناور مینیمال و دارک‌مود، با زدن کلید `Enter` متن را در کلیپ‌بورد قرار داده و جایگزین می‌کند.
4. رویدادهای اصلاح را در دیتابیس محلی (SQLite) ذخیره می‌کند تا بدون نیاز به سرور، پروفایل یادگیری شخصی کاربر ساخته شود.

---

## 📁 ساختار مخزن (Repository Structure)

```text
/home/sajjad/Desktop/AI_Enginniering/writing_assistant/
│
├── README.md                      # راهنمای اصلی مخزن و خلاصه وضعیت پروژه
│
├── docs/                          # اسناد تحلیلی و کانتکست کامل پروژه
│   ├── 01_BRD.md                  # سند رسمی نیازمندی‌های محصول و معماری نهایی (v2.2)
│   ├── 02_CONTEXT_AND_EVOLUTION.md # تاریخچه، دیالوگ‌ها و روند شکل‌گیری ایده از ابتدا تا اکنون
│   ├── 03_DECISION_LOG.md         # لاگ تصمیمات کلیدی معماری و محصول (ADRs)
│   ├── 04_TECHNICAL_SPIKE_1.md    # گزارش رسمی نتایج موفقیت‌آمیز تست زنده اسپایک در Wayland
│   └── 05_IN_PLACE_POPUP_PLAN.md  # سند معماری و طرح پاپ‌آپ در کنار باکس نوشتن (GNOME Adapter + Core)
│
└── prototype/                     # کد نمونه اولیه و اجرایی
    └── spike_hud.py               # اسکریپت زنده پنجره شناور GTK4 با پشتیبانی Wayland
```

---

## 🚀 وضعیت کنونی پروژه (Current Status)

* **✅ Milestone 0 — Technical Spike #1 (Passed):**
  * اثبات استخراج متن سلکت‌شده در Wayland و بررسی رفتار Pop-Shell.
* **✅ Milestone 1 — In-Place Popup & Core Engine (Implemented & 100% Tested):**
  * **متدولوژی Spec-Kit:** اجرای کامل چرخه `specify → plan → tasks → analyze → implement` و تکمیل ۳۵ تسک مهندسی‌شده.
  * **هسته منطقی (Core Engine):** پیاده‌سازی پکیج پایتونی `src/writing_companion` با پروتکل تک‌مرحله‌ای JSON، چک‌پوینت معنایی فارسی، حفاظت از کدها و دیتابیس SQLite محلی با مد WAL.
  * **پرووایدرهای هوش مصنوعی:** پشتیبانی آماده از `MockProvider` (آفلاین)، `GroqProvider` (مدل Llama 3.3 70B زیر ۳۰۰ms)، `GeminiProvider` و `OllamaProvider`.
  * **آداپتور کامپوزیتور گنوم:** افزونه `extension/` با پاپ‌آپ درجا کنار ماوس (`global.get_pointer()`) مصون از تایلینگ Pop-Shell، و جایگزینی خودکار متن با فشردن کلید `Enter` (شبیه‌ساز `Shift + Insert`).
  * **تست‌های خودکار:** ۱۳ تست خودکار یکپارچگی و یونیت (همگی پاس‌شده).

---

## ⌨️ نحوه اجرا و راه‌اندازی (Quickstart)

### ۱. فعال‌سازی محیط پایتون و اجرای تست‌ها:
```bash
# ساخت محیط و نصب پکیج
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# اجرای تست‌های خودکار
pytest
```

### ۲. تست مستقیم هسته در ترمینال (بدون نیاز به کلید API):
```bash
# تست عبارت هیبرید با کلمه فارسی داخل براکت
python3 -m writing_companion.cli --text "Can we [سازگار کنیم] this function with new API?"

# تست جمله بدون اشتباه (Minimal Intervention)
python3 -m writing_companion.cli --text "This pull request resolves the memory leak."
```

### ۳. اتصال به مدل‌های ابری (اختیاری):
برای استفاده از مدل‌های واقعی ابری، کافیست در ریشه پروژه یک فایل `.env` بسازید:
```env
GROQ_API_KEY=gsk_...
# یا
GEMINI_API_KEY=AIza...
```

### ۴. فعال‌سازی اکستنشن دسکتاپ:
اکستنشن در مسیر `~/.local/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com` نصب شده است. پس از یک بار ورود مجدد (Log Out / Log In) به سشن دسکتاپ:
1. هر متنی را در VS Code یا هر محیط دیگری انتخاب کنید.
2. کلید **`Ctrl + Alt + G`** را فشار دهید.
3. با زدن **`Enter`** متن جایگزین می‌شود و با **`Esc`** پاپ‌آپ بسته می‌شود.

