# KeyCRM Dialog Exporter

Локальний Python-додаток з кнопкою **«Парсити поточний чат»**:
- ви відкриваєте потрібний діалог у KeyCRM;
- натискаєте кнопку в програмі;
- увесь видимий текст повідомлень зберігається у новий `.txt` файл.

Кожне натискання створює **окремий файл** (з timestamp у назві).

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Підготовка Chrome

Скрипт підключається до відкритого Chrome через DevTools.

1. Повністю закрийте Chrome.
2. Запустіть його з прапором:

```bash
google-chrome --remote-debugging-port=9222
```

Windows приклад:

```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

3. У цьому вікні Chrome відкрийте KeyCRM і потрібний чат.
4. Якщо треба вигрузити старі повідомлення — прокрутіть чат вгору, щоб вони підвантажились.

## Запуск застосунку

```bash
python keycrm_dialog_exporter.py
```

## Як це працює

- шукає на сторінці контейнер `.vac-messages-container`;
- проходить по `.vac-message-wrapper`;
- бере текст із `.vac-format-message-wrapper`;
- додає час із `.vac-message-date` та ім'я відправника;
- якщо тексту немає, але є вкладення — ставить `[Вкладення]`;
- зберігає результат у `exports/<timestamp>_<chat_name>.txt`.

## Важливо

- Експортуються тільки повідомлення, які **вже є в DOM** (завантажені у відкритому чаті).
- Якщо KeyCRM змінить CSS-класи/верстку, селектори треба буде оновити у файлі `keycrm_dialog_exporter.py`.
