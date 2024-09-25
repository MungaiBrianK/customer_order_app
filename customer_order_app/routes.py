from flask import Blueprint, redirect, url_for, session, request, jsonify, render_template, Flask
from customer_order_app.models import db, Customer, Order
from customer_order_app import oauth  # Import the initialized oauth instance
from datetime import datetime
import binascii
import os
import africastalking

# Define the routes blueprint
main = Blueprint('main', __name__)

def generate_nonce():
    return binascii.b2a_hex(os.urandom(16)).decode('utf-8')

# Initialize Africa's Talking
africastalking.initialize(username='app-customer-order', api_key='atsk_a772794f78ca3b289e4aa2d6a36ac2d803300bd92de083bae5fb6d7493796bf5f084c18d')
sms = africastalking.SMS

def send_sms(phone_number, message):
    try:
        # Debugging: Print the SMS details before sending
        print(f"Attempting to send SMS to {phone_number} with message: {message}")

        # Send the SMS using Africa's Talking API
        response = sms.send(message, [phone_number])
        
        # Debugging: Log the entire API response for better insights
        print(f"SMS API Response: {response}")

        # Check for the success/failure of the SMS
        if 'SMSMessageData' in response and 'Recipients' in response['SMSMessageData']:
            recipients = response['SMSMessageData']['Recipients']
            for recipient in recipients:
                if recipient['status'] == 'Success':
                    print(f"SMS successfully sent to {recipient['number']}!")
                else:
                    print(f"SMS failed for {recipient['number']}: {recipient['status']}")
        else:
            print("SMS API did not return expected data.")
        
        return response
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return None

def create_app(config_name):
    app = Flask(__name__)

    # Configure the app
    app.config['SECRET_KEY'] = '9RDcyhM8K50jsA8X4ZymxVMdsBkO_VnrpMLbuJuX5YXDXZi0d7pXV5nc1RTuzRdC'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['TESTING'] = True
    app.config['DEBUG'] = True

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main)

    return app

# Login route
@main.route('/login')
def login():
    redirect_uri = url_for('main.callback', _external=True)
    if not redirect_uri.startswith('https'):
        redirect_uri = redirect_uri.replace('http', 'https', 1)
    
    nonce = generate_nonce()  # Generate a secure nonce
    session['nonce'] = nonce  # Store nonce in session
    print(f"Storing nonce: {nonce}")  # Debugging statement

    return oauth.auth0.authorize_redirect(
        redirect_uri,
        nonce=nonce
    )

# Callback route
@main.route('/callback')
def callback():
    nonce = session.pop('nonce', None)  # Retrieve nonce from session
    print(f"Retrieved nonce: {nonce}")  # Debugging statement

    if nonce is None:
        return jsonify({"error": "Nonce missing"}), 400

    try:
        token = oauth.auth0.authorize_access_token()
        user_info = oauth.auth0.parse_id_token(token, nonce=nonce)  # Pass nonce to validate it
        session['user'] = user_info
        print(f"User info: {user_info}")

        return redirect(url_for('main.dashboard'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Logout route
@main.route('/logout')
def logout():
    session.clear()
    return redirect(
        f"https://{app.config['AUTH0_DOMAIN']}/v2/logout?returnTo=" + url_for('main.home', _external=True)
    )

# Dashboard route
@main.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('main.login'))

    user_info = session['user']
    print(f"User info in dashboard: {user_info}")
    customers = db.session.query(Customer).all()
    orders = db.session.query(Order).all()
    return render_template('dashboard.html', user_info=user_info, customers=customers, orders=orders)

# Add customer route
@main.route('/customers', methods=['POST'])
def add_customer():
    data = request.get_json()
    print(f"Received data: {data}")  # Debugging statement
    name = data.get('name')
    code = data.get('code')
    phone_number = data.get('phone_number')

    if not name or not code or not phone_number:
        return jsonify({"error": "Customer data incomplete"}), 400

    try:
        new_customer = Customer(name=name, code=code, phone_number=phone_number)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({"message": "Customer added successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")  # Debugging statement
        return jsonify({"error": str(e)}), 500

# Add order route
@main.route('/orders', methods=['POST'])
def add_order():
    data = request.get_json()
    print(f"Received data: {data}")  # Debugging statement

    item = data.get('item')
    amount = data.get('amount')
    customer_code = data.get('customer_code')

    if not item or not amount or not customer_code:
        return jsonify({"error": "Order data incomplete"}), 400

    customer = db.session.query(Customer).filter_by(code=customer_code).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    # Debugging: Print customer details
    print(f"Customer found: ID={customer.id}, Name={customer.name}, Phone={customer.phone_number}")

    try:
        new_order = Order(customer_id=customer.id, item=item, amount=amount, timestamp=datetime.utcnow())
        db.session.add(new_order)
        db.session.commit()

        # Debugging: Print before sending SMS
        print(f"Sending SMS to {customer.phone_number} with message: 'Hello {customer.name}, your order for {item} has been successfully placed.'")

        # Send SMS notification to the customer
        sms_message = f"Hello {customer.name}, your order for {item} has been successfully placed."
        response = send_sms(customer.phone_number, sms_message)

        # Debugging: Print the response from Africa's Talking
        print(f"SMS Response: {response}")

        return jsonify({"message": "Order added successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")  # Debugging statement
        return jsonify({"error": str(e)}), 500

# Route to display the customers page
@main.route('/customers', methods=['GET'])
def customers_page():
    if 'user' not in session:
        return redirect(url_for('main.login'))

    user_info = session['user']  # Get user info from session
    customers = db.session.query(Customer).all()  # Fetch all customers from the database
    return render_template('customers.html', user_info=user_info, customers=customers)  # Pass user_info to template

# Route to display the orders page
@main.route('/orders', methods=['GET'])
def orders_page():
    if 'user' not in session:
        return redirect(url_for('main.login'))

    user_info = session['user']  # Get user info from session
    orders = db.session.query(Order).all()  # Fetch all orders from the database
    return render_template('orders.html', user_info=user_info, orders=orders)  # Pass user_info to template

# Route to display the manage page
@main.route('/manage')
def manage():
    customers = db.session.query(Customer).all()
    orders = db.session.query(Order).all()
    return render_template('manage.html', customers=customers, orders=orders)

# Route to delete all customers
@main.route('/delete_all_customers', methods=['POST'])
def delete_all_customers():
    try:
        db.session.query(Customer).delete()
        db.session.commit()
        return jsonify({"message": "All customers have been deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Route to delete all orders
@main.route('/delete_all_orders', methods=['POST'])
def delete_all_orders():
    try:
        db.session.query(Order).delete()
        db.session.commit()
        return jsonify({"message": "All orders have been deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


