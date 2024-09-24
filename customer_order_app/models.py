from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'phone_number': self.phone_number
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    item = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))

    def as_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'item': self.item,
            'amount': self.amount,
            'timestamp': self.timestamp.isoformat()
        }
