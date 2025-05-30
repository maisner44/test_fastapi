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

TEST_METHODS = ["Ручне тестування", "Автоматизоване тестування", "ШІ тестування"]
CRITERIA_COUNT = 5
VALUES_PER_CRITERION = 3

CRITERIA_NAMES = [
    "Час виконання тестування (у годинах)",
    "Кількість виконаних тест-кейсів (за 1 сесію)",
    "Кількість знайдених багів",
    "Відсоток покриття функціоналу",
    "Стабільність результатів (% успішних повторних запусків)"
]

# Глобальна змінна для історії (у реальному додатку використовуйте БД)
analysis_history = []

def calculate_scores(criteria_values):
    scores = [0, 0, 0]  # Бали для кожного методу
    
    # Критерій 1: Час виконання (годин)
    time = criteria_values[0]
    if time[0] > 3:   scores[0] += 1
    elif 2 <= time[0] <= 3: scores[0] += 2
    elif 1 <= time[0] < 2: scores[0] += 3
    elif 0.5 <= time[0] < 1: scores[0] += 4
    elif time[0] < 0.5: scores[0] += 5
    
    if time[1] > 3:   scores[1] += 1
    elif 2 <= time[1] <= 3: scores[1] += 2
    elif 1 <= time[1] < 2: scores[1] += 3
    elif 0.5 <= time[1] < 1: scores[1] += 4
    elif time[1] < 0.5: scores[1] += 5
    
    if time[2] > 3:   scores[2] += 1
    elif 2 <= time[2] <= 3: scores[2] += 2
    elif 1 <= time[2] < 2: scores[2] += 3
    elif 0.5 <= time[2] < 1: scores[2] += 4
    elif time[2] < 0.5: scores[2] += 5
    
    # Критерій 2: Тест-кейси
    cases = criteria_values[1]
    for i, val in enumerate(cases):
        if val <= 5: scores[i] += 1
        elif 6 <= val <= 10: scores[i] += 2
        elif 11 <= val <= 20: scores[i] += 3
        elif 21 <= val <= 30: scores[i] += 4
        elif val > 30: scores[i] += 5
    
    # Критерій 3: Баги
    bugs = criteria_values[2]
    for i, val in enumerate(bugs):
        if val <= 1: scores[i] += 1
        elif 2 <= val <= 3: scores[i] += 2
        elif val == 4: scores[i] += 3
        elif val == 5: scores[i] += 4
        elif val >= 6: scores[i] += 5
    
    # Критерій 4: Покриття
    coverage = criteria_values[3]
    for i, val in enumerate(coverage):
        if val < 20: scores[i] += 1
        elif 20 <= val < 40: scores[i] += 2
        elif 40 <= val < 60: scores[i] += 3
        elif 60 <= val < 80: scores[i] += 4
        elif val >= 80: scores[i] += 5
    
    # Критерій 5: Стабільність
    stability = criteria_values[4]
    for i, val in enumerate(stability):
        if val < 60: scores[i] += 1
        elif 60 <= val < 75: scores[i] += 2
        elif 75 <= val < 85: scores[i] += 3
        elif 85 <= val < 95: scores[i] += 4
        elif val >= 95: scores[i] += 5
    
    return scores

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(CRITERIA_COUNT),
        "values_count": range(VALUES_PER_CRITERION),
        "criteria_names": CRITERIA_NAMES,
        "test_methods": TEST_METHODS,
        "result": "",
        "form_data": {f"crit_{i}_val_{j}": "" for i in range(CRITERIA_COUNT) for j in range(VALUES_PER_CRITERION)},
        "history_count": len(analysis_history)
    })

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_criteria(request: Request):
    form_data = await request.form()
    
    # Збираємо значення
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
    
    # Розраховуємо бали
    scores = calculate_scores(criteria_values)
    
    # Формуємо список результатів і сортуємо його за балами (від більшого до меншого)
    results = sorted(
        zip(TEST_METHODS, scores),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Формуємо текст результату
    result_text = "Результати оцінки методів (відсортовано за балами):\n\n"
    for method, score in results:
        result_text += f"{method}: {score} балів\n"
    
    # Додаємо до історії
    history_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "criteria": criteria_values,
        "results": [{"method": m, "score": s} for m, s in results]  # Зберігаємо відсортовані результати
    }
    analysis_history.append(history_entry)
    
    # Зберігаємо введені значення для відображення
    saved_data = {f"crit_{i}_val_{j}": str(criteria_values[i][j]) 
                 for i in range(CRITERIA_COUNT) for j in range(VALUES_PER_CRITERION)}
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(CRITERIA_COUNT),
        "values_count": range(VALUES_PER_CRITERION),
        "criteria_names": CRITERIA_NAMES,
        "test_methods": TEST_METHODS,
        "result": result_text,
        "form_data": saved_data,
        "history_count": len(analysis_history)
    })

@app.post("/clear_history")
async def clear_history():
    global analysis_history
    analysis_history = []
    return {"message": "Історія очищена", "count": 0}

@app.get("/export")
async def export_to_excel():
    if not analysis_history:
        return {"message": "Історія порожня"}
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Результати оцінки"
    
    # Заголовки
    headers = ["Дата оцінки", "Метод тестування", "Бали"]
    for crit in CRITERIA_NAMES:
        headers.extend([f"{crit} (значення 1)", f"{crit} (значення 2)", f"{crit} (значення 3)"])
    ws.append(headers)
    
    # Дані
    for entry in analysis_history:
        for result in entry["results"]:
            row = [
                entry["date"],
                result["method"],
                result["score"]
            ]
            # Додаємо значення критеріїв
            for crit_values in entry["criteria"]:
                row.extend(crit_values)
            ws.append(row)
    
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    headers = {
        "Content-Disposition": "attachment; filename=analysis_history.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    return StreamingResponse(excel_file, headers=headers)