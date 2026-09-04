import json
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session'  # Нужно для работы сессий

DATA_FILE = 'data.json'

# Единые пароли для входа
PASSWORDS = {
    'user': 'class2026',
    'admin': 'admin2026'
}

# Инициализация JSON-файла базовыми данными, если его нет
def init_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "tasks": [
                {"id": 1, "text": "Собрать деньги на экскурсию", "status": "todo"},
                {"id": 2, "text": "Обсудить выпускной альбом", "status": "doing"},
                {"id": 3, "text": "Закупить рабочие тетради", "status": "done"}
            ],
            "schedule": "Понедельник - Пятница: 8:30 - 14:00",
            "contacts": [
                {"role": "Председатель РК", "name": "Иванова Мария", "phone": "+7 (999) 111-22-33"},
                {"role": "Казначей", "name": "Петрова Ольга", "phone": "+7 (999) 222-33-44"}
            ]
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'role' in session:
        return redirect(url_for('board'))
    
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORDS['admin']:
            session['role'] = 'admin'
            return redirect(url_for('board'))
        elif password == PASSWORDS['user']:
            session['role'] = 'user'
            return redirect(url_for('board'))
        else:
            error = "Неверный пароль класса!"
            
    return render_template('login.html', error=error)

@app.route('/board', methods=['GET', 'POST'])
def board():
    if 'role' not in session:
        return redirect(url_for('login'))
        
    data = load_data()
    
    if request.method == 'POST' and session['role'] == 'admin':
        action = request.form.get('action')
        
        if action == 'add':
            task_text = request.form.get('task_text')
            if task_text:
                new_id = max([t['id'] for t in data['tasks']], default=0) + 1
                data['tasks'].append({"id": new_id, "text": task_text, "status": "todo"})
                save_data(data)
                
        elif action == 'move':
            task_id = int(request.form.get('task_id'))
            new_status = request.form.get('status')
            for task in data['tasks']:
                if task['id'] == task_id:
                    task['status'] = new_status
                    break
            save_data(data)
            
        elif action == 'delete':
            task_id = int(request.form.get('task_id'))
            data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
            save_data(data)
            
        return redirect(url_for('board'))

    return render_template('board.html', tasks=data['tasks'], role=session['role'])

@app.route('/contacts')
def contacts():
    if 'role' not in session:
        return redirect(url_for('login'))
    data = load_data()
    return render_template('contacts.html', contacts=data['contacts'], schedule=data['schedule'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_data()
    # Читаем порт из переменной окружения Яндекса (по умолчанию 5000)
    port = int(os.environ.get("PORT", 5000))
    # Запускаем на адресе 0.0.0.0, чтобы сервер принимал внешние запросы
    app.run(host="0.0.0.0", port=port)
