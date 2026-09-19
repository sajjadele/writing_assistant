# گزارش فنی اسپایک شماره ۱ (Technical Spike #1 Report)
## استخراج متن انتخاب‌شده، کلید میانبر سراسری و پنجره شناور در Ubuntu Wayland

* **تاریخ اجرا:** ۱۸ سپتامبر ۲۰۲۶  
* **محیط تست:** Ubuntu 24.04 LTS | GNOME Shell 46.0 | Session: `wayland-0`  
* **وضعیت نهایی:** ✅ **موفقیت‌آمیز (Passed)**  

---

## ۱. هدف اسپایک (Objective)
اثبات اینکه آیا می‌توان در محیط لینوکس اوبونتو روی نمایشگر مدرن Wayland:
1. متنی را که کاربر در هر برنامه‌ای (مرورگر، پیام‌رسان، IDE یا ترمینال) با ماوس هایلایت کرده، خواند؟
2. با یک کلید میانبر سراسری (Global Shortcut)، پنجره شناور سریع (HUD) را بدون اختلال فوکوس باز کرد؟
3. متن اصلاح‌شده را با زدن `Enter` در کلیپ‌بورد سیستم قرار داد و پنجره را بست؟

---

## ۲. یافته‌های تشخیصی و موانع پلتفرم (Diagnostics & Findings)

### ۲.۱. شکست ابزارهای سنتی در Wayland
* اجرای ابزار سنتی `xdotool getactivewindow` با خطای قطعی زیر متوقف شد:
  ```text
  XGetWindowProperty[_NET_ACTIVE_WINDOW] failed (code=1)
  xdo_get_active_window reported an error
  ```
  **نتیجه:** در Wayland پنجره‌ها ایزوله هستند و ابزارهای متکی بر سرور قدیمی X11 نمی‌توانند پنجره‌های فعال را بازرسی کنند.

### ۲.۲. راهکار قطعی و نیتیو: `wl-clipboard`
* با نصب بسته استاندارد `wl-clipboard`، ابزار `wl-paste --primary` مورد آزمایش قرار گرفت.
* **نتیجه:** متن هایلایت‌شده با ماوس در برنامه‌های Wayland (بدون نیاز به فشردن کلید `Ctrl+C`) بلافاصله با تاخیر نزدیک به صفر در خروجی استاندارد دریافت شد.

### ۲.۳. کشف نحوه پیست خودکار در افزونه‌های گنوم
* در بررسی کدهای اکستنشن فعال سیستم کاربر (`clipboard-indicator@tudmotu.com`) مشخص شد که ارسال کلیدهای مجازی درون Mutter با استفاده از دستگاه مجازی Clutter و کلید جهانی **`Shift + Insert`** انجام می‌شود:
  ```javascript
  // Clutter.get_default_backend().get_default_seat().create_virtual_device(KEYBOARD_DEVICE)
  this.keyboard.press(Clutter.KEY_Shift_L);
  this.keyboard.press(Clutter.KEY_Insert);
  ```

---

## ۳. پیاده‌سازی و تنظیم کلید میانبر سراسری (Global Shortcut)

### ۳.۱. حل تداخل کلید در گنوم
* بررسی شد که کلید پرطرفدار `Super + G` قبلاً توسط افزونه مدیریت پنجره `Pop-Shell` (`toggle-floating`) اشغال شده بود.
* کلید ترکیبی **`Ctrl + Alt + G`** (`<Primary><Alt>g`) انتخاب شد که کاملاً آزاد بود.

### ۳.۲. دستور ثبت شورتکات در تنظیمات گنوم:
```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
"['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/', \
  '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/', \
  '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/']"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'English Companion Spike'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command '/usr/bin/python3 /home/sajjad/Desktop/AI_Enginniering/writing_assistant/prototype/spike_hud.py'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>g'
```

---

## ۴. نتایج آزمون عملی کاربر (User Validation)
کاربر به صورت زنده متن را در برنامه‌های فعال سلکت کرد، کلید میانبر را فشرد:
* پنجره شناور بلافاصله در مرکز صفحه با استایل تیره و شیک ظاهر شد.
* متن ورودی، پیشنهاد انگلیسی، چِک‌پوینت معنایی (برداشت من از منظورتان) و نکته آموزشی با فونت و جهت‌بندی صحیح نمایش داده شد.
* با فشردن `Enter`، متن پیشنهادشده در کلیپ‌بورد ذخیره و پنجره بسته شد.
* با فشردن `Ctrl + V`، متن جدید با موفقیت پیست شد.

**نتیجه‌گیری:** فاز اسپایک با موفقیت ۱۰۰٪ پایان یافت و اعتبار فنی معماری اثبات شد.
