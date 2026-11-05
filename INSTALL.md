# Mindcatch — встановлення з нуля (для не-програміста)

Мета: запустити Mindcatch за 5 хвилин, не читаючи код. Все працює локально на
вашому комп'ютері, дані не залишають пристрій.

## Що потрібно

- **Windows 10/11** або **Linux** (Ubuntu/Debian/Fedora — будь-який).
- **Python 3.12+** (безкоштовно, з python.org).
- Інтернет лише один раз — щоб завантажити Python і бібліотеки. Далі Mindcatch
  працює офлайн.

## Windows

### 1. Встановіть Python

1. Відкрийте https://www.python.org/downloads/ → кнопка **Download Python 3.x**.
2. Запустіть завантажений файл. **Важливо:** на першому екрані поставте
   галочку **«Add python.exe to PATH»** → **Install Now**.
3. Перевірка: натисніть <kbd>Win</kbd>+<kbd>R</kbd>, введіть `cmd`, Enter,
   потім у чорному вікні наберіть `python --version` — має показати версію.

### 2. Завантажте Mindcatch

Натисніть зелену кнопку **Code → Download ZIP** на сторінці проєкту,
розпакуйте архів у зручну папку (наприклад, `Документи\Mindcatch`).

*Або через Git (якщо встановлений):*

```
git clone https://github.com/bigpi/mindcatch.git
```

### 3. Запуск

Відкрийте папку проєкту і **двічі клацніть `scripts\start.bat`**.

Скрипт сам: створить ізольоване середовище, встановить залежності, запустить
сервер і відкриє браузер на `http://localhost:8000`. Наступні запуски —
миттєві.

Вручну (якщо надаєте перевагу терміналу):

```
cd шлях\до\mindcatch
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

### 4. Автозапуск разом із Windows (опційно)

1. Натисніть <kbd>Win</kbd>+<kbd>R</kbd>, введіть `shell:startup`, Enter —
   відкриється папка автозавантаження.
2. Скопіюйте туди **ярлик** `start.bat` (права кнопка на файлі → «Створити
   ярлик» → перемістіть ярлик у папку автозавантаження).

Тепер Mindcatch стартує сам при вході в систему і працює у фоні.

### 5. Встановлення як застосунок (PWA)

Відкрийте `http://localhost:8000` у Chrome/Edge → адресний рядок → іконка
«Встановити». З'явиться окреме вікно застосування з власною іконкою в меню
«Пуск».

## Linux

### 1. Встановіть Python (зазвичай уже встановлений)

```
python3 --version   # потрібно 3.12+
```

### 2. Завантажте і запустіть

```
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python3 -m pip install --user -r requirements.txt
python3 -m uvicorn app.main:app --port 8000
```

Відкрийте `http://localhost:8000`.

### 3. Автозапуск через systemd user unit

Створіть файл `~/.config/systemd/user/mindcatch.service`:

```ini
[Unit]
Description=Mindcatch — local thought capture
After=network.target

[Service]
ExecStart=%h/.local/bin/uvicorn app.main:app --port 8000
WorkingDirectory=%h/mindcatch
Restart=on-failure

[Install]
WantedBy=default.target
```

(Замініть `WorkingDirectory` на ваш шлях до папки проєкту, а `ExecStart` —
на шлях до uvicorn: `which uvicorn` підкаже.)

Активуйте:

```
systemctl --user daemon-reload
systemctl --user enable --now mindcatch
```

Щоб сервіс працював і коли ви не увійшли: `sudo loginctl enable-linger $USER`.

## Оновлення

1. Збережіть дані: у застосунку натисніть «⬇ Експорт» → JSON (або просто
   скопіюйте файл `mindcatch.db` з папки проєкту).
2. Оновіть код:

```
git pull          # якщо клонували через git
```

(якщо завантажували ZIP — завантажте новий ZIP і замініть папку, `mindcatch.db`
зберігається).

3. Оновіть залежності: `python -m pip install -r requirements.txt`.
4. Запустіть знову — база даних мігрує автоматично, нічого конвертувати не треба.

## Де живуть мої дані

Один файл SQLite поруч із проєктом: `mindcatch.db` (створюється при першому
запуску). Резервна копія = скопіювати цей файл. Нічего не відправляється в
інтернет; нагадування показуються локально через браузер.

## Часті проблеми

| Симптом | Рішення |
|---|---|
| `python не є внутрішньою програмою` | перевстановіть Python з галочкою «Add to PATH» |
| Порт 8000 зайнятий | запустіть `start.bat` — він сам шукає вільний порт; або вкажіть інший порт у команді uvicorn |
| Нагадування не з'являються | дозвольте сповіщення, коли браузер запитає (запит приходить після першого capture) |
| OCR не працює | це опційно: встановіть Tesseract або вводьте текст вручну |
