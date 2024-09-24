import os
import binascii
from flask import Blueprint, redirect, url_for, session, request, jsonify, render_template, Flask
from customer_order_app.models import db, Customer, Order
from customer_order_app import oauth
from datetime import datetime
import africastalking

# Define the routes blueprint
main = Blueprint('main', __name__)

# Utility function to generate nonce
def generate_nonce():
    return binascii.b2a_hex(os.urandom(16)).decode('utf-8')

# Initialize Africa's Talking API securely
africastalking.initialize(
    username=os.getenv('AT_USERNAME', 'app-customer-order'),
    api_key=os.getenv('AT_API_KEY')
)
sms = africastalking.SMS

# Utility function to send SMS using Africa's Talking
def send_sms(phone_number, message):
    try:
        print(f"Sending SMS to {phone_number}: {message}")
        response = sms.send(message, [phone_number])
        if 'SMSMessageData' in response and 'Recipients' in response['SMSMessageData']:
            recipients = response['SMSMessageData']['Recipients']
            for recipient in recipients:
                if recipient['status'] == 'Success':
                    print(f"SMS successfully sent to {recipient['number']}.")
                else:
                    print(f"SMS failed for {recipient['number']}: {recipient['status']}")
        else:
            print("Unexpected SMS API response.")
        return response
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None

# Initialize the Flask app
def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_name)  # Load configuration from object
    db.init_app(app)
    app.register_blueprint(main)
    return app

# Login route
@main.route('/login')
def login():
    redirect_uri = url_for('main.callback', _external=True)
    redirect_uri = redirect_uri.replace('http', 'https', 1)
    nonce = generate_nonce()
    session['nonce'] = nonce
    print(f"Storing nonce: {nonce}")
    return oauth.auth0.authorize_redirect(redirect_uri, nonce=nonce)

# OAuth callback route
@main.route('/callback')
def callback():
    nonce = session.pop('nonce', None)
    print(f"Retrieved nonce: {nonce}")
    if nonce is None:
        return jsonify({"error": "Nonce missing"}), 400
    try:
        token = oauth.auth0.authorize_access_token()
        user_info = oauth.auth0.parse_id_token(token, nonce=nonce)
        session['user'] = user_info
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Logout route
@main.route('/logout')
def logout():
    session.clear()
    return redirect(f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?returnTo=" + url_for('main.home', _external=True))

# Dashboard route
@main.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    customers = Customer.query.all()
    orders = Order.query.all()
    return render_template('dashboard.html', user_info=session['user'], customers=customers, orders=orders)

# Add customer route
@main.route('/customers', methods=['POST'])
def add_customer():
    data = request.get_json()
    if not all([data.get('name'), data.get('code'), data.get('phone_number')]):
        return jsonify({"error": "Customer data incomplete"}), 400
    try:
        new_customer = Customer(**data)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({"message": "Customer added successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Add order route
@main.route('/orders', methods=['POST'])
def add_order():
    data = request.get_json()
    if not all([data.get('item'), data.get('amount'), data.get('customer_code')]):
        return jsonify({"error": "Order data incomplete"}), 400

    customer = Customer.query.filter_by(code=data['customer_code']).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    try:
        new_order = Order(customer_id=customer.id, item=data['item'], amount=data['amount'], timestamp=datetime.utcnow())
        db.session.add(new_order)
        db.session.commit()

        sms_message = f"Hello {customer.name}, your order for {data['item']} has been placed."
        response = send_sms(customer.phone_number, sms_message)
        print(f"SMS Response: {response}")
        return jsonify({"message": "Order added successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Get customers route
@main.route('/customers', methods=['GET'])
def customers_page():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    customers = Customer.query.all()
    return render_template('customers.html', user_info=session['user'], customers=customers)

# Get orders route
@main.route('/orders', methods=['GET'])
def orders_page():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    orders = Order.query.all()
    return render_template('orders.html', user_info=session['user'], orders=orders)

# Manage page route
@main.route('/manage')
def manage():
    customers = Customer.query.all()
    orders = Order.query.all()
    return render_template('manage.html', customers=customers, orders=orders)

# Delete all customers route
@main.route('/delete_all_customers', methods=['POST'])
def delete_all_customers():
    try:
        db.session.query(Customer).delete()
        db.session.commit()
        return jsonify({"message": "All customers deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Delete all orders route
@main.route('/delete_all_orders', methods=['POST'])
def delete_all_orders():
    try:
        db.session.query(Order).delete()
        db.session.commit()
        return jsonify({"message": "All orders deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
