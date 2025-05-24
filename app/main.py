from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openpyxl
from io import BytesIO
from datetime import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

TEST_METHODS = ["Метод A", "Метод B", "Метод C"]
CRITERIA_COUNT = 5
VALUES_PER_CRITERION = 3

# Глобальна змінна для історії (у реальному додатку використовуйте БД)
analysis_history = []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(1, CRITERIA_COUNT + 1),
        "values_count": range(1, VALUES_PER_CRITERION + 1),
        "result": "",
        "history_count": len(analysis_history)
    })

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_criteria(request: Request):
    form_data = await request.form()
    
    criteria_values = []
    for criterion_idx in range(CRITERIA_COUNT):
        values = []
        for value_idx in range(VALUES_PER_CRITERION):
            key = f"crit_{criterion_idx}_val_{value_idx}"
            try:
                value = float(form_data.get(key, 0))
            except ValueError:
                value = 0
            values.append(value)
        criteria_values.append(values)
    
    # Логіка оцінки методів
    def evaluate_method(method_idx, criteria_values):
        total = 0
        for i, values in enumerate(criteria_values):
            avg = sum(values) / len(values)
            if method_idx == 0:  # Метод A
                total += avg * (1.5 if i < 2 else 0.8)
            elif method_idx == 1:  # Метод B
                total += avg * (1.5 if 2 <= i < 4 else 0.8)
            else:  # Метод C
                total += avg * (2.0 if i == 4 else 0.5)
        return round(total, 2)
    
    results = []
    for method_idx, method_name in enumerate(TEST_METHODS):
        score = evaluate_method(method_idx, criteria_values)
        results.append({"method": method_name, "score": score})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Формуємо результат
    result_text = "Результати оцінки методів:\n\n"
    for res in results:
        result_text += f"{res['method']}: {res['score']} балів\n"
    
    # Додаємо до історії
    history_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "criteria": criteria_values,
        "results": results
    }
    analysis_history.append(history_entry)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(1, CRITERIA_COUNT + 1),
        "values_count": range(1, VALUES_PER_CRITERION + 1),
        "result": result_text,
        "history_count": len(analysis_history)
    })

@app.get("/export")
async def export_to_excel():
    if not analysis_history:
        return {"message": "Історія порожня"}
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Результати оцінки"
    
    # Заголовки
    headers = ["Дата оцінки", "Метод тестування", "Бали"]
    for crit in range(1, CRITERIA_COUNT + 1):
        headers.append(f"Критерій {crit} (середнє)")
    ws.append(headers)
    
    # Дані
    for entry in analysis_history:
        for result in entry["results"]:
            row = [
                entry["date"],
                result["method"],
                result["score"]
            ]
            # Додаємо середні значення критеріїв
            for crit_values in entry["criteria"]:
                row.append(round(sum(crit_values) / len(crit_values), 2))
            ws.append(row)
    
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    headers = {
        "Content-Disposition": "attachment; filename=analysis_history.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    return StreamingResponse(excel_file, headers=headers)

@app.post("/clear_history")
async def clear_history():
    global analysis_history
    analysis_history = []
    return {"message": "Історія очищена", "count": 0}