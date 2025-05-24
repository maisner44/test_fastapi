from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

# Налаштування бази даних
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель для зберігання результатів
class CalculationHistory(Base):
    __tablename__ = "calculation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    calculation_date = Column(DateTime, default=datetime.now)
    input_data = Column(String)  # JSON-рядок з вхідними даними
    results = Column(String)     # JSON-рядок з результатами
    summary = Column(String)     # Текстовий підсумок

# Створюємо таблиці
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Методи тестування
TEST_METHODS = ["Метод A", "Метод B", "Метод C"]
CRITERIA_COUNT = 5
VALUES_PER_CRITERION = 3

# Залежність для отримання сесії БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    # Отримуємо історію з БД
    history = db.query(CalculationHistory).order_by(CalculationHistory.calculation_date.desc()).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(1, CRITERIA_COUNT + 1),
        "values_count": range(1, VALUES_PER_CRITERION + 1),
        "result": "",
        "history": history
    })

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_criteria(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    
    # Збираємо введені значення
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
    
    # Оцінюємо методи
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
    
    # Отримуємо результати
    results = []
    for method_idx, method_name in enumerate(TEST_METHODS):
        score = evaluate_method(method_idx, criteria_values)
        results.append({"method": method_name, "score": score})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Формуємо текст результату
    result_text = "Результати оцінки методів:\n\n"
    for res in results:
        result_text += f"{res['method']}: {res['score']} балів\n"
    
    # Зберігаємо в історію
    history_record = CalculationHistory(
        input_data=str(criteria_values),
        results=str(results),
        summary=result_text
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)
    
    # Отримуємо оновлену історію
    history = db.query(CalculationHistory).order_by(CalculationHistory.calculation_date.desc()).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "criteria_count": range(1, CRITERIA_COUNT + 1),
        "values_count": range(1, VALUES_PER_CRITERION + 1),
        "result": result_text,
        "history": history
    })