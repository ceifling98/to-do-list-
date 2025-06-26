from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta, datetime
import os
import csv
from io import StringIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(100), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    repeat_interval = db.Column(db.String(20), nullable=True)  # 'daily', 'weekly', 'biweekly', 'monthly', 'yearly', or None
    pinned = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(10), nullable=True, default='Medium')  # 'High', 'Medium', 'Low'
    list_name = db.Column(db.String(100), nullable=True)  # For multi-list/project support
    created_at = db.Column(db.Date, nullable=False, default=date.today)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Date, nullable=False, default=date.today)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)  # Link to Task, nullable for global notes

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'Task' or 'Note'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    deleted = db.Column(db.Boolean, default=False)
    original_id = db.Column(db.Integer, nullable=True)  # For restoring

def create_db():
    if not os.path.exists('tasks.db'):
        db.create_all()

def log_history(item_type, content, deleted, original_id=None):
    h = History(type=item_type, content=content, timestamp=datetime.now(), deleted=deleted, original_id=original_id)
    db.session.add(h)
    db.session.commit()

@app.route('/')
def index():
    show = request.args.get('show')
    category = request.args.get('category')
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'due')
    list_name = request.args.get('list')
    today = date.today()
    query = Task.query
    if list_name:
        query = query.filter_by(list_name=list_name)
    if show == 'undone':
        query = query.filter_by(done=False)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Task.task.ilike(f'%{search}%') | Task.category.ilike(f'%{search}%'))
    # Sorting
    if sort == 'name':
        query = query.order_by(Task.pinned.desc(), Task.task.asc())
    elif sort == 'created':
        query = query.order_by(Task.pinned.desc(), Task.created_at.asc())
    else:  # default: due
        query = query.order_by(Task.pinned.desc(), Task.due_date.asc().nullslast(), Task.id.asc())
    tasks = query.all()
    categories = [c[0] for c in db.session.query(Task.category).distinct() if c[0]]
    lists = [l[0] for l in db.session.query(Task.list_name).distinct() if l[0]]
    due_soon = [t for t in tasks if t.due_date and not t.done and t.due_date <= today]
    return render_template('index.html', tasks=tasks, show=show, category=category, categories=categories, due_soon=due_soon, today=today, search=search, sort=sort, lists=lists, list_name=list_name)

@app.route('/add', methods=['POST'])
def add():
    task_description = request.form.get('task')
    category = request.form.get('category')
    due_date_str = request.form.get('due_date')
    repeat_interval = request.form.get('repeat_interval')
    priority = request.form.get('priority', 'Medium')
    list_name = request.form.get('list_name')
    due_date = None
    if due_date_str:
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            due_date = None
    if task_description:
        new_task = Task(task=task_description, done=False, category=category, due_date=due_date, repeat_interval=repeat_interval, priority=priority, list_name=list_name, created_at=date.today())
        db.session.add(new_task)
        db.session.commit()
        log_history('Task', task_description, deleted=False, original_id=new_task.id)
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>', methods=['POST'])
def complete(task_id):
    task = Task.query.get_or_404(task_id)
    task.done = True
    # If recurring, create next occurrence
    if task.repeat_interval and task.due_date:
        if task.repeat_interval == 'daily':
            next_due = task.due_date + timedelta(days=1)
        elif task.repeat_interval == 'weekly':
            next_due = task.due_date + timedelta(weeks=1)
        elif task.repeat_interval == 'biweekly':
            next_due = task.due_date + timedelta(weeks=2)
        elif task.repeat_interval == 'monthly':
            # Add 1 month, handle month overflow
            month = task.due_date.month + 1
            year = task.due_date.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(task.due_date.day, [31,29 if year%4==0 and (year%100!=0 or year%400==0) else 28,31,30,31,30,31,31,30,31,30,31][month-1])
            try:
                next_due = task.due_date.replace(year=year, month=month, day=day)
            except ValueError:
                next_due = None
        elif task.repeat_interval == 'yearly':
            try:
                next_due = task.due_date.replace(year=task.due_date.year + 1)
            except ValueError:
                next_due = None
        else:
            next_due = None
        if next_due:
            new_task = Task(task=task.task, done=False, category=task.category, due_date=next_due, repeat_interval=task.repeat_interval)
            db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/uncomplete/<int:task_id>', methods=['POST'])
def uncomplete(task_id):
    task = Task.query.get_or_404(task_id)
    task.done = False
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    task = Task.query.get_or_404(task_id)
    log_history('Task', task.task, deleted=True, original_id=task.id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/task/<int:task_id>')
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template('task_detail.html', task=task)

@app.route('/lists', methods=['POST'])
def add_list():
    list_name = request.form.get('list_name')
    if list_name:
        # No DB table for lists, just use as string
        pass
    return redirect(url_for('index', list=list_name))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        new_description = request.form.get('task')
        new_category = request.form.get('category')
        due_date_str = request.form.get('due_date')
        repeat_interval = request.form.get('repeat_interval')
        priority = request.form.get('priority', 'Medium')
        list_name = request.form.get('list_name')
        due_date = None
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
            except ValueError:
                due_date = None
        if new_description:
            task.task = new_description
            task.category = new_category
            task.due_date = due_date
            task.repeat_interval = repeat_interval
            task.priority = priority
            task.list_name = list_name
            db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', task=task, task_id=task_id)

@app.route('/pin/<int:task_id>', methods=['POST'])
def pin(task_id):
    task = Task.query.get_or_404(task_id)
    task.pinned = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/unpin/<int:task_id>', methods=['POST'])
def unpin(task_id):
    task = Task.query.get_or_404(task_id)
    task.pinned = False
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    # Analytics: % complete, tasks/week, top categories
    tasks = Task.query.all()
    complete = sum(1 for t in tasks if t.done)
    incomplete = sum(1 for t in tasks if not t.done)
    # Tasks per week (last 8 weeks)
    from collections import Counter
    import datetime
    weeks = [(date.today() - timedelta(weeks=i)).isocalendar()[:2] for i in range(8)][::-1]
    week_labels = [f"{y}-W{w}" for (y, w) in weeks]
    week_counts = Counter((t.created_at.isocalendar()[:2] for t in tasks))
    week_data = [week_counts.get((y, w), 0) for (y, w) in weeks]
    # Top categories
    cat_counts = Counter(t.category for t in tasks if t.category)
    top_cats = cat_counts.most_common(6)
    top_labels = [c[0] for c in top_cats]
    top_data = [c[1] for c in top_cats]
    return render_template('dashboard.html',
        completion_data={'complete': complete, 'incomplete': incomplete},
        tasks_per_week={'labels': week_labels, 'data': week_data},
        top_categories={'labels': top_labels, 'data': top_data}
    )

@app.route('/export/csv')
def export_csv():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Task', 'Category', 'Due Date', 'Repeat', 'Priority', 'List', 'Done', 'Created'])
    for t in Task.query.all():
        cw.writerow([t.task, t.category, t.due_date, t.repeat_interval, t.priority, t.list_name, t.done, t.created_at])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=tasks.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/export/pdf')
def export_pdf():
    # Simple HTML to PDF export using pdfkit (requires wkhtmltopdf)
    import pdfkit
    tasks = Task.query.all()
    html = render_template('task_detail.html', task=tasks[0])  # For demo, export first task
    pdf = pdfkit.from_string(html, False)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=tasks.pdf'
    return response

@app.route('/public/<list_name>')
def public_list(list_name):
    tasks = Task.query.filter_by(list_name=list_name).all()
    return render_template('index.html', tasks=tasks, show=None, category=None, categories=[], due_soon=[], today=date.today(), search='', sort='due', lists=[list_name], list_name=list_name, public=True)

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "To-Do List App",
        "short_name": "To-Do",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f9fafb",
        "theme_color": "#2563eb",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.route('/service-worker.js')
def service_worker():
    sw = '''self.addEventListener('install', e => {self.skipWaiting();});
self.addEventListener('fetch', e => {});'''
    response = make_response(sw)
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/calendar')
def calendar_view():
    tasks = Task.query.filter(Task.due_date.isnot(None)).all()
    events = []
    for t in tasks:
        events.append({
            'id': t.id,
            'title': t.task + (f' [{t.category}]' if t.category else ''),
            'start': t.due_date.isoformat(),
            'color': '#2563eb' if not t.done else '#a3a3a3',
            'textColor': '#fff',
            'allDay': True
        })
    return render_template('calendar.html', calendar_events=events)

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    from sqlalchemy import desc
    all_tasks = Task.query.order_by(Task.created_at.desc()).all()
    selected_task_id = None
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        task_id = request.form.get('task_id')
        if content:
            note = Note(content=content, created_at=date.today(), task_id=task_id if task_id else None)
            db.session.add(note)
            db.session.commit()
            log_history('Note', content, deleted=False, original_id=note.id)
            selected_task_id = int(task_id) if task_id else None
            return redirect(url_for('notes'))
    latest_note = Note.query.order_by(desc(Note.id)).first()
    note_content = latest_note.content if latest_note else ''
    return render_template(
        'notes.html',
        note_content=note_content,
        all_tasks=all_tasks,
        selected_task_id=selected_task_id
    )

@app.route('/task/<int:task_id>/notes', methods=['GET', 'POST'])
def task_notes(task_id):
    task = Task.query.get_or_404(task_id)
    from sqlalchemy import desc
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            note = Note(content=content, created_at=date.today(), task_id=task_id)
            db.session.add(note)
            db.session.commit()
            return redirect(url_for('task_notes', task_id=task_id))
    notes = Note.query.filter_by(task_id=task_id).order_by(desc(Note.id)).all()
    return render_template('task_notes.html', task=task, notes=notes,
        completion_data={'complete': 0, 'incomplete': 0},
        tasks_per_week={'labels': [], 'data': []},
        top_categories={'labels': [], 'data': []}
    )

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/history')
def history():
    history_items = History.query.order_by(History.timestamp.desc()).all()
    return render_template('history.html', history_items=history_items)

@app.route('/history/clear', methods=['POST'])
def clear_history():
    History.query.delete()
    db.session.commit()
    return redirect(url_for('history'))

@app.route('/history/restore/<int:history_id>', methods=['POST'])
def restore_task(history_id):
    h = History.query.get_or_404(history_id)
    if h.type == 'Task' and h.deleted and h.original_id:
        # Only restore if not already present
        if not Task.query.get(h.original_id):
            new_task = Task(id=h.original_id, task=h.content, done=False, created_at=h.timestamp.date())
            db.session.add(new_task)
            db.session.commit()
            h.deleted = False
            db.session.commit()
    return redirect(url_for('history'))

if __name__ == '__main__':
    with app.app_context():
        create_db()
    app.run(debug=True)
