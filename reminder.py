# -*- coding: utf-8 -*-
"""
reminder.py — напоминание пить воду.

Простой скрипт для Windows 10. Работает без установки сторонних библиотек.
Каждый день в заданное время:
  1) пишет сообщение в консоль;
  2) показывает всплывающее уведомление Windows;
  3) делает запись в лог-файл reminder.log.

Запуск: python reminder.py
Остановка: Ctrl+C
"""

import os
import sys
import time
from datetime import datetime

# ============================================================
# НАСТРОЙКИ (можно менять под себя)
# ============================================================

# Расписание напоминаний: (часы, минуты)
# Всего 6 раз в день по 250 мл = 1500 мл
SCHEDULE = [
    (8, 0),    # 08:00
    (10, 30),  # 10:30
    (13, 0),   # 13:00
    (15, 30),  # 15:30
    (18, 0),   # 18:00
    (20, 30),  # 20:30
]

# Сколько мл воды нужно выпить за один раз
PORTION_ML = 250

# Текст уведомления
TITLE = "Время пить воду!"
TEXT = "Выпей {ml} мл воды. Цель дня: 1500 мл.".format(ml=PORTION_ML)

# Файл лога лежит рядом со скриптом
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminder.log")

# Как часто проверять часы (секунд). Больше значение — меньше нагрузки на компьютер.
CHECK_INTERVAL_SEC = 20

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def write_log(message):
    """
    Добавить одну строку в лог-файл с текущей датой и временем.
    Файл открывается в режиме "добавить" (a), поэтому старые записи не удаляются.
    """
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("[{stamp}] {message}\n".format(stamp=stamp, message=message))
    except OSError as e:
        # Если лог писать не получается (нет прав, диск отключен) — просто пишем в консоль
        print("Не удалось записать в лог: {0}".format(e))


def show_notification(title, text):
    """
    Показать всплывающее уведомление средствами Windows 10.
    Используем PowerShell и WinRT-класс ToastNotificationManager —
    это встроенное средство, ничего устанавливать не нужно.
    Если что-то не получится, вернём False и скрипт продолжит работу.
    """
    # Экранируем одинарные кавычки, чтобы текст не сломал команду PowerShell
    safe_title = title.replace("'", "''")
    safe_text = text.replace("'", "''")

    # PowerShell-скрипт: создаём XML тоста и показываем его в центре уведомлений
    ps_script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
        "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        "$textNodes = $template.GetElementsByTagName('text'); "
        "$textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) | Out-Null; "
        "$textNodes.Item(1).AppendChild($template.CreateTextNode('{text}')) | Out-Null; "
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('WaterReminder').Show($toast);"
    ).format(title=safe_title, text=safe_text)

    try:
        import subprocess
        # CREATE_NO_WINDOW = 0x08000000 — чтобы мельком не мелькало чёрное окно консоли
        flags = 0x08000000 if os.name == "nt" else 0
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-Command", ps_script],
            check=False,
            timeout=15,
            creationflags=flags,
        )
        return True
    except Exception as e:
        print("Не удалось показать уведомление: {0}".format(e))
        return False


def make_message():
    """Текст, который показываем в консоли и в уведомлении."""
    now = datetime.now().strftime("%H:%M")
    return "{time} — пора пить воду! Выпей {ml} мл.".format(time=now, ml=PORTION_ML)


def build_done_key(hour, minute, day_key):
    """
    Уникальный ключ для напоминания за конкретный день.
    Нужен, чтобы одно и то же напоминание не сработало дважды за сутки.
    """
    return "{day}-{h:02d}:{m:02d}".format(day=day_key, h=hour, m=minute)


# ============================================================
# ОСНОВНАЯ ПРОГРАММА
# ============================================================

def main():
    print("Скрипт напоминаний запущен. Расписание:")
    for h, m in SCHEDULE:
        print("  - {h:02d}:{m:02d}  ({ml} мл)".format(h=h, m=m, ml=PORTION_ML))
    print("Всего за день: {total} мл.".format(total=len(SCHEDULE) * PORTION_ML))
    print("Остановка — Ctrl+C.")
    print("Лог пишется в файл: {0}".format(LOG_FILE))
    print("-" * 50)

    write_log("Скрипт запущен")

    # Множество уже выполненных напоминаний за текущий день
    done = set()
    current_day = datetime.now().strftime("%Y-%m-%d")

    try:
        while True:
            now = datetime.now()
            day_key = now.strftime("%Y-%m-%d")

            # Наступил новый день — разрешаем напоминания снова
            if day_key != current_day:
                current_day = day_key
                done.clear()
                write_log("Новый день: {0}".format(day_key))

            for (h, m) in SCHEDULE:
                key = build_done_key(h, m, day_key)
                if key in done:
                    continue  # это напоминание уже было сегодня

                # Считаем, сколько секунд осталось до нужного момента
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                diff = (target - now).total_seconds()

                # Сработало, если время наступило (или прошло не больше минуты назад)
                if -60 < diff <= 0:
                    message = make_message()
                    print(message)
                    shown = show_notification(TITLE, TEXT)
                    if shown:
                        write_log("Напоминание {h:02d}:{m:02d} показано".format(h=h, m=m))
                    else:
                        write_log("Напоминание {h:02d}:{m:02d} показано только в консоли".format(h=h, m=m))
                    done.add(key)

            time.sleep(CHECK_INTERVAL_SEC)

    except KeyboardInterrupt:
        # Пользователь нажал Ctrl+C — аккуратно завершаемся
        print("\nСкрипт остановлен пользователем (Ctrl+C).")
        write_log("Скрипт остановлен пользователем (Ctrl+C)")
    except Exception as e:
        # Любая другая ошибка — тоже записываем в лог
        print("Произошла ошибка: {0}".format(e))
        write_log("Ошибка: {0}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
