import africastalking

def send_sms(to, message):
    # Initialize the Africa's Talking SDK
    africastalking.initialize(
        username='app-customer-order',
        api_key='atsk_7aee832cfb045c33ad9b0c27a9203ae833b6a8053b8b67652b976fa40055947f2d728be2'
    )
    
    sms = africastalking.SMS
    
    try:
        response = sms.send(message, [to])
        print(f"SMS sent successfully: {response}")
        return response
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None
