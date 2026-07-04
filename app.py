import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from Utils.detector import TabletDetector
import cv2
import numpy as np
import webbrowser
import threading

BASE_DIR = r'L:\NeuroApp'
TEMPLATE_DIR = r'L:\NeuroApp\templates'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'results')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'tablet-counter-secret-key'

detector = TabletDetector()

# ===== БАЗА ДАННЫХ SQLITE =====
DB_PATH = os.path.join(BASE_DIR, 'history.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            tablet_count INTEGER,
            empty_count INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Пустое имя файла'}), 400

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({'error': 'Разрешены только изображения (jpg, png, bmp)'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = f'original_{timestamp}.jpg'
    temp_path = os.path.join(UPLOAD_FOLDER, original_filename)
    file.save(temp_path)

    try:
        result_img, tablet_count, empty_count = detector.detect(temp_path)

        result_filename = f'result_{timestamp}.jpg'
        result_path = os.path.join(UPLOAD_FOLDER, result_filename)
        cv2.imwrite(result_path, result_img)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO requests (timestamp, filename, tablet_count, empty_count) VALUES (?, ?, ?, ?)',
            (datetime.now().isoformat(), result_filename, tablet_count, empty_count)
        )
        conn.commit()
        conn.close()

        return jsonify({
            'result_image': f'/static/results/{result_filename}',
            'tablet_count': tablet_count,
            'empty_count': empty_count,
            'total_cells': tablet_count + empty_count
        })

    except Exception as e:
        print(f"[ERROR] Ошибка при обработке: {e}")
        return jsonify({'error': 'Ошибка при обработке изображения'}), 500

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, filename, tablet_count, empty_count FROM requests ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    history = [
        {'timestamp': row[0], 'filename': row[1], 'tablet_count': row[2], 'empty_count': row[3]}
        for row in rows
    ]
    return jsonify(history)

@app.route('/export/pdf')
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont('Times-Roman', 'C:/Windows/Fonts/times.ttf'))
    
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, filename, tablet_count, empty_count FROM requests ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Times-Roman", 16)
    c.drawString(30, height - 30, "Отчёт по контролю комплектации блистеров")
    
    c.setFont("Times-Roman", 12)
    c.drawString(30, height - 55, "Дата генерации: " + datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    
    y = height - 80
    c.setFont("Times-Roman", 11)
    
    for i, (ts, fname, tc, ec) in enumerate(rows, 1):
        try:
            dt = datetime.fromisoformat(ts)
            ts_str = dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            ts_str = ts
        
        c.drawString(30, y, f"{i}. {ts_str} | Файл: {fname} | Таблеток: {tc} | Пустых: {ec} | Всего: {tc+ec}")
        y -= 20
        if y < 40:
            c.showPage()
            c.setFont("Times-Roman", 11)
            y = height - 40

    c.save()
    buffer.seek(0)
    
    return buffer.getvalue(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename=report.pdf'
    }

@app.route('/export/excel')
def export_excel():
    from openpyxl import Workbook
    from io import BytesIO

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, filename, tablet_count, empty_count FROM requests ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Контроль комплектации"
    ws.append(["№", "Дата и время", "Файл", "Таблеток", "Пустых ячеек", "Всего ячеек"])

    for i, (ts, fname, tc, ec) in enumerate(rows, 1):
        try:
            dt = datetime.fromisoformat(ts)
            ts_str = dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            ts_str = ts
        ws.append([i, ts_str, fname, tc, ec, tc + ec])

    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 40)
        ws.column_dimensions[column_letter].width = adjusted_width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.getvalue(), 200, {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename=report.xlsx'
    }

def open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')
    print("[INFO] Браузер открыт!")

if __name__ == '__main__':
    print("="*50)
    print("ЗАПУСК ВЕБ-ПРИЛОЖЕНИЯ ДЛЯ КОНТРОЛЯ КОМПЛЕКТАЦИИ БЛИСТЕРОВ")
    print("="*50)
    print("[INFO] Сервер запускается на http://127.0.0.1:5000")
    print("[INFO] Браузер откроется автоматически через 1.5 секунды")
    print("="*50)
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)