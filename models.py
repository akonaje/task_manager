from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import ForeignKey, Index


db = SQLAlchemy()


class TaskHistory(db.Model):
    __tablename__ = 'TaskHistory'
    __table_args__ = (
        db.Index('ix_TaskHistory_task_id', 'task_id'),  # Index on task_id
    )
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.task_id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey('classifications.classification_id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    task = db.relationship('Task', back_populates='history')


class Classification(db.Model):
    __tablename__ = 'classifications'
    __table_args__ = (
        db.Index('ix_Classification_name', 'name'),  # Index on name
    )
    
    classification_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  
    tasks = db.relationship('Task', back_populates='classification')


class Task(db.Model):
    __tablename__ = 'tasks'
    __table_args__ = (
        db.Index('ix_Task_priority', 'priority'),                    # Index on priority
        db.Index('ix_Task_status', 'status')                         # Index on status
    )
    
    task_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey('classifications.classification_id'))
    
    classification = db.relationship('Classification', back_populates='tasks')
    history = db.relationship('TaskHistory', back_populates='task', cascade="all, delete-orphan")
