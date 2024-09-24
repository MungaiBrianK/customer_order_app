import unittest
from customer_order_app.routes import create_app, db

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')  # Use the updated configuration
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_customer(self):
        response = self.client.post('/customers', json={
            'name': 'John Doe',
            'code': 'C123',
            'phone_number': '+254783623070'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Customer added successfully', response.data)

    def test_add_order(self):
        # First add a customer
        self.client.post('/customers', json={
            'name': 'John Doe',
            'code': 'C123',
            'phone_number': '+254783623070'
        })
        
        response = self.client.post('/orders', json={
            'item': 'Widget',
            'amount': 10,
            'customer_code': 'C123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order added successfully', response.data)

if __name__ == '__main__':
    unittest.main()
