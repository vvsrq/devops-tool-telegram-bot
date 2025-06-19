import requests
import html
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime
import logging
import re
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def escape_markdown(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2"""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)

TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
ALLOW_CHAT_ID= int(os.getenv("ALLOW_CHAT_ID"))
REPORT_PATH = '/home/students/tiog/report.txt'

METRICS = {
    'rps': {
        'query': 'rate(http_request_duration_seconds_count[1m])',
        'description': 'RPS (запросов в минуту)'
    },
    'avg_response_time': {
        'query': 'rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])',
        'description': 'Среднее время отклика (сек.)'
    },
    '5xx_rate': {
        'query': 'sum(rate(http_request_duration_seconds_count{code=~"5.."}[1m]))',
        'description': 'Частота ошибок 5xx (в сек.)'
    },
    'cpu_usage': {
        'query': '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
        'description': 'Загрузка CPU (%)'
    },
    'memory_usage': {
        'query': '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100',
        'description': 'Загрузка памяти (%)'
    }
}

async def active_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOW_CHAT_ID:
        return
    try:
        result = subprocess.run(['ss', '-tunap'], stdout=subprocess.PIPE, text=True)
        lines = result.stdout.strip().split('\n')[1:]  # пропустить заголовок

        formatted_lines = []
        for line in lines[:30]:
            parts = line.split()
            if len(parts) >= 6:
                proto = parts[0]
                state = parts[1]
                local = parts[4]
                peer = parts[5]
                formatted_lines.append(f"{proto:<5} {state:<12} {local:<25} {peer}")

        output = '\n'.join(formatted_lines)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(REPORT_PATH, 'w') as f:
            f.write(f"Отчёт об активных соединениях — {timestamp}\n")
            f.write("Протокол Статус       Локальный адрес           Удалённый адрес\n")
            f.write("=" * 70 + "\n")
            f.write(output)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(REPORT_PATH, 'rb'),
            caption="🔌  Активные соединения"
        )

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def get_network_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOW_CHAT_ID:
        return
    try:
        result = subprocess.run(['vnstat', '--oneline'], stdout=subprocess.PIPE, text=True)
        fields = result.stdout.strip().split(';')
        iface = fields[1]
        date = fields[2]
        rx = fields[3]
        tx = fields[4]
        total = fields[5]
        speed = fields[6]
        msg = (
            f"📶  *Сетевой трафик* ({iface}) на {date}:\n"
            f"⬇️ Приём: {rx}\n"
            f"⬆️ Передача: {tx}\n"
            f"📊  Всего: {total}\n"
            f"⚡  Средняя скорость: {speed}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def get_top_ips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOW_CHAT_ID:
        return
    try:
        cmd = (
            "netstat -ntu | awk '{print $5}' | cut -d: -f1 | "
            "grep -Eo '([0-9]{1,3}\\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -n 10"
        )
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        lines = result.stdout.strip().split('\n')
        cleaned = '\n'.join(line for line in lines if line.strip())
        message = f"🌐  <b>Топ IP-адресов:</b>\n<pre>{cleaned}</pre>"
        await update.message.reply_text(message[:4096], parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def get_metric_value(query):
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query})
        data = response.json()
        results = data['data']['result']
        metrics = []

        for item in results:
            instance = item['metric'].get('instance', 'unknown')
            value = item['value'][1]  # Второе значение в массиве "value"
            metrics.append((instance, value))

        return metrics

    except Exception as e:
        print(f"Ошибка при получении метрик: {e}")
        return []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOW_CHAT_ID:
        return
    await update.message.reply_text("Привет! Я работаю только в этом чате.")

async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOW_CHAT_ID:
        return

    message = "📊  *Метрики приложения:*\n"

    for key, metric in METRICS.items():
        results = get_metric_value(metric['query'])
        desc = escape_markdown(metric['description'])

        if not results:
            message += f"\n*{desc}*: `Нет данных`"
        else:
            message += f"\n*{desc}*:"
            for instance, value in results:
                inst = escape_markdown(instance)
                val = escape_markdown(value)
                message += f"\n  `{inst}` → `{val}`"

    await update.message.reply_markdown_v2(message)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('metrics', metrics))
    app.add_handler(CommandHandler('netstat', active_connections))
    app.add_handler(CommandHandler('traffic', get_network_traffic))
    app.add_handler(CommandHandler('topips', get_top_ips))
    app.add_error_handler(error_handler)

    app.run_polling()



if __name__ == '__main__':
    run_bot()