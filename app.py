from flask import Flask, render_template, request, redirect, url_for
from models import db, Task, TaskHistory, Classification
from datetime import datetime
from flask import flash
from sqlalchemy.orm import aliased
from sqlalchemy.sql import text
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'isolation_level': 'SERIALIZABLE'
}
db.init_app(app)


# prepared statement version of add task

@app.route('/add', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        try:
            # transaction begins
            with db.session.begin():
                name = request.form['name']
                due_date_str = request.form['due_date']
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                priority = request.form['priority']
                status = request.form['status']

                # Prepared statement for classification lookup or creation
                new_classification_name = request.form.get('new_classification', '').strip()
                classification_id = None

                if new_classification_name: # if new classification added
                    classification_id = db.session.execute(
                        text("""
                        INSERT INTO classifications (name)
                        VALUES (:name)
                        ON CONFLICT(name) DO UPDATE SET name = :name
                        RETURNING classification_id
                        """),
                        {"name": new_classification_name}
                    ).scalar()
                else:
                    classification_id = request.form.get('classification_id') # gets classification if not new
                
                # Prepared statement to insert the new task
                db.session.execute(
                    text("""
                    INSERT INTO tasks (name, due_date, priority, status, classification_id)
                    VALUES (:name, :due_date, :priority, :status, :classification_id)
                    """),
                    {"name": name, "due_date": due_date, "priority": priority, "status": status, "classification_id": classification_id}
                )
                # db.session.commit()

                # commit is automatic upon session.begin()
                return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}", 500

    classifications = Classification.query.all() # gets all classifications and sends to template
    return render_template('add_task.html', classifications=classifications)



## prepared statements for edit

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    try:
        # transaction starts
        with db.session.begin():
            # Fetch the task using a prepared statement
            task = db.session.execute(
                text("SELECT * FROM tasks WHERE task_id = :task_id"),
                {"task_id": task_id}
            ).fetchone()
            
            if not task:
                return "Task not found", 404

            if request.method == 'POST':
                # Get updated form data
                name = request.form['name']
                due_date_str = request.form['due_date']
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                priority = request.form['priority']
                status = request.form['status']
                classification_id = request.form.get('classification_id') # fetches the classification for the update

                # Insert a history record using a prepared statement
                db.session.execute(
                    text("""
                    INSERT INTO TaskHistory (task_id, name, due_date, priority, status, classification_id, timestamp)
                    VALUES (:task_id, :name, :due_date, :priority, :status, :classification_id, :timestamp)
                    """),
                    {
                        "task_id": task_id,
                        "name": name,
                        "due_date": due_date,
                        "priority": priority,
                        "status": status,
                        "classification_id": classification_id,
                        "timestamp": datetime.now()
                    }
                )

                # Update the task using a prepared statement
                db.session.execute(
                    text("""
                    UPDATE tasks
                    SET name = :name,
                        due_date = :due_date,
                        priority = :priority,
                        status = :status,
                        classification_id = :classification_id
                    WHERE task_id = :task_id
                    """),
                    {
                        "name": name,
                        "due_date": due_date,
                        "priority": priority,
                        "status": status,
                        "classification_id": classification_id,
                        "task_id": task_id
                    }
                )

                # Commit the changes to the database
                # db.session.commit()

                return redirect(url_for('index'))
            
    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {e}", 500

    # For GET requests, fetch classifications and render the edit form
    classifications = db.session.execute(
        text("SELECT * FROM classifications")
    ).fetchall() 

    return render_template('edit_task.html', task=task, classifications=classifications)


# prepared statement for delete
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    try:
        with db.session.begin():
            db.session.execute(
                text("DELETE FROM tasks WHERE task_id = :task_id"),
                {"task_id": task_id}
            )
           # db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {e}", 500


# ORM for task history access
@app.route('/task_history/<int:task_id>')
def task_history(task_id):
    task = Task.query.get(task_id)
    if not task:
        return "Task not found", 404
    # TaskHistory or task_history?
    history_records = TaskHistory.query.filter_by(task_id=task_id).order_by(TaskHistory.timestamp.desc()).all()
    return render_template('task_history.html', task=task, history_records=history_records)


PRIORITY_MAPPING = {
    'High': 1,
    'Medium': 2,
    'Low': 3
}

def calculate_average_priority(tasks):
    if not tasks:
        return 0
    total_priority = sum(PRIORITY_MAPPING[task.priority] for task in tasks if task.priority in PRIORITY_MAPPING)
    return total_priority / len(tasks) if len(tasks) > 0 else 0


def apply_filters(query):
    filter_name = request.args.get('filter_name')
    filter_due_date = request.args.get('filter_due_date')
    filter_priority = request.args.get('filter_priority')
    filter_status = request.args.get('filter_status')
    filter_classification_id = request.args.get('filter_classification_id')
    filter_classification_id = int(filter_classification_id) if filter_classification_id else None

    if filter_name:
        query = query.filter(Task.name.ilike(f"%{filter_name}%"))
    if filter_due_date:
        query = query.filter(Task.due_date == filter_due_date)
    if filter_priority:
        query = query.filter(Task.priority == filter_priority)
    if filter_status:
        query = query.filter(Task.status == filter_status)
    if filter_classification_id:
        query = query.filter(Task.classification_id == filter_classification_id)

    return query


@app.route('/')
def index():
    tasks_query = Task.query.options(joinedload(Task.classification))
    tasks_query = apply_filters(tasks_query)

    # Execute the query
    tasks = tasks_query.all()

    # Calculate statistics
    total_filtered_tasks = len(tasks)
    completed_tasks = [task for task in tasks if task.status == 'Completed']
    completed_tasks_count = len(completed_tasks)

    average_completed = (completed_tasks_count / total_filtered_tasks * 100) if total_filtered_tasks > 0 else 0
    productivity_rate = (completed_tasks_count / total_filtered_tasks * 100) if total_filtered_tasks > 0 else 0

    # Calculate average priority of filtered tasks
    average_priority = calculate_average_priority(tasks)

    # Get classifications for the filter dropdown
    classifications = Classification.query.all()

    # Render the filtered tasks and classifications, including statistics
    return render_template('index.html', 
                           tasks=tasks, 
                           classifications=classifications,
                           average_completed=average_completed,
                           productivity_rate=productivity_rate,
                           average_priority=average_priority)



if __name__ == '__main__':
    app.run(debug=True)

