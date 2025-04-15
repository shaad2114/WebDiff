from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import difflib
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import os
import tempfile

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

def save_to_excel(comparison_result):
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparison"

    headers = ['Line Number', 'Archived Text', 'Current Text', 'Status']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")

    for idx, (old_line, new_line, status) in enumerate(comparison_result, start=1):
        ws.append([idx, old_line, new_line, status])

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    wb.save(temp_file.name)
    return temp_file.name

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        archived_url = request.form['archived_url']
        current_url = request.form['current_url']
        try:
            archived_text = get_text_from_url(archived_url)
            current_text = get_text_from_url(current_url)
            comparison_result = compare_and_align_lines(archived_text, current_text)
            excel_path = save_to_excel(comparison_result)
            return send_file(excel_path, as_attachment=True, download_name='comparison_report.xlsx')
        except Exception as e:
            return f"<h2>Error occurred:</h2><pre>{e}</pre>"
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
