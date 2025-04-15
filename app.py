from flask import Flask, request, send_file, jsonify
import requests
from bs4 import BeautifulSoup
import difflib
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import os
from datetime import datetime

app = Flask(__name__)

def get_text_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    return soup.get_text(separator='\n', strip=True)

def compare_and_align_lines(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    result = []

    for opcode, i1, i2, j1, j2 in sm.get_opcodes():
        if opcode == 'equal':
            for i in range(i2 - i1):
                result.append((old_lines[i1 + i], new_lines[j1 + i], 'Unchanged'))
        elif opcode == 'replace':
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                old_line = old_lines[i1 + k] if k < (i2 - i1) else ''
                new_line = new_lines[j1 + k] if k < (j2 - j1) else ''
                status = 'Changed' if old_line and new_line else 'Removed' if old_line else 'Added'
                result.append((old_line, new_line, status))
        elif opcode == 'delete':
            for i in range(i1, i2):
                result.append((old_lines[i], '', 'Removed'))
        elif opcode == 'insert':
            for j in range(j1, j2):
                result.append(('', new_lines[j], 'Added'))

    return result

def save_to_excel(data, save_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparison"

    headers = ['Line No.', 'Archived Text', 'Current Text', 'Status']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")

    for idx, (old, new, status) in enumerate(data, start=1):
        ws.append([idx, old, new, status])

    wb.save(save_path)

@app.route('/compare', methods=['POST'])
def compare():
    data = request.json
    url1 = data.get('archived_url')
    url2 = data.get('current_url')

    if not url1 or not url2:
        return jsonify({'error': 'Both URLs are required'}), 400

    try:
        text1 = get_text_from_url(url1)
        text2 = get_text_from_url(url2)
        comparison = compare_and_align_lines(text1, text2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f'comparisons/diff_{timestamp}.xlsx'
        os.makedirs('comparisons', exist_ok=True)
        save_to_excel(comparison, file_path)

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return "WebDiff API - Post to /compare"

if __name__ == '__main__':
    app.run(debug=True)