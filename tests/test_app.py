import pytest
from customer_order_app import create_app, db
from customer_order_app.models import Customer, Order
from flask import json

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    # Create some test data
    customer1 = Customer(name="John Doe", code="C001", phone_number="123456789")
    customer2 = Customer(name="Jane Doe", code="C002", phone_number="987654321")
    
    order1 = Order(customer_id=1, item="Laptop", amount=1200.00)
    order2 = Order(customer_id=2, item="Phone", amount=800.00)
    
    db.session.add(customer1)
    db.session.add(customer2)
    db.session.add(order1)
    db.session.add(order2)
    db.session.commit()

    yield db

    # Cleanup after test
    db.session.remove()
    db.drop_all()

# Test login route
def test_login(client):
    response = client.get('/login')
    assert response.status_code == 302  # Assuming it redirects to Auth0

# Test add customer route
def test_add_customer(client, init_database):
    data = {
        'name': 'Alice Doe',
        'code': 'C003',
        'phone_number': '555555555'
    }
    response = client.post('/customers', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    assert b"Customer added successfully" in response.data

    # Check if customer is added to the database
    customer = Customer.query.filter_by(name="Alice Doe").first()
    assert customer is not None
    assert customer.code == 'C003'

# Test add order route
def test_add_order(client, init_database):
    data = {
        'item': 'Tablet',
        'amount': 300.00,
        'customer_code': 'C001'
    }
    response = client.post('/orders', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    assert b"Order added successfully" in response.data

    # Check if order is added to the database
    order = Order.query.filter_by(item="Tablet").first()
    assert order is not None
    assert order.amount == 300.00

# Test dashboard route
def test_dashboard(client, init_database):
    # Simulate a logged-in user
    with client.session_transaction() as sess:
        sess['user'] = {'name': 'Test User'}

    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b"Customers" in response.data
    assert b"Orders" in response.data

# Test delete all customers
def test_delete_all_customers(client, init_database):
    response = client.post('/delete_all_customers')
    assert response.status_code == 200
    assert b"All customers have been deleted" in response.data

    # Verify customers are deleted
    customers = Customer.query.all()
    assert len(customers) == 0

# Test delete all orders
def test_delete_all_orders(client, init_database):
    response = client.post('/delete_all_orders')
    assert response.status_code == 200
    assert b"All orders have been deleted" in response.data

    # Verify orders are deleted
    orders = Order.query.all()
    assert len(orders) == 0
