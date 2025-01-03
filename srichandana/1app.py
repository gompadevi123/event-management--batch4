from flask import Flask, render_template, request, flash, session, redirect, url_for
import mysql.connector
from mysql.connector import Error  # For Database interactions
from flask_mail import Mail, Message  # For sending Emails
from itsdangerous import URLSafeTimedSerializer  # For secure Token Generation
import random
import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
import mysql.connector
import requests  # Ensure this is imported for making HTTP requests
import uuid  # Ensure this is imported for generating UUIDs


app = Flask(__name__)

app.secret_key = 'sri'  # Required for session management and flashing messages
# An instance of flask app is created with a secret key
# In-memory storage for registered users (for demonstration purposes)


# Database connection function
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',  
            user='root',       
            password='Sri/123@',  
            database='event_management'  
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# About Page
@app.route('/about')
def about():
    return render_template('about.html')

# Registration Page (for users)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        mobile = request.form['mobile']
        dob = request.form['dob']
        email = request.form['email']
        city = request.form['city']
        state = request.form['state']
        role = request.form['role']  
        

        connection = create_connection()

        if connection:
            try:
                cursor = connection.cursor()
                
                # Check if username already exists
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                existing_user = cursor.fetchone()

                if existing_user:
                    flash("Username already exists.", "error")
                    return redirect(url_for('register'))

                # Insert the new user into the database - storing in the users table 
                insert_query = """INSERT INTO users (username, password, mobile, dob, email, city, state, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(insert_query, (username, password, mobile, dob, email, city, state, role))
                connection.commit()  # Commit after inserting user

                flash("Registration successful! Please log in.", "success")

                # Get the newly created user ID
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                user_id = cursor.fetchone()[0]  # Get the user ID

                # Insert into customers table - user_id
                customer_query = """INSERT INTO customers (name, email, user_id) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE user_id=%s"""
                cursor.execute(customer_query, (username, email, user_id, user_id))

                # Insert into events table - user_id
                event_query = """INSERT INTO events (organizer_name, user_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE user_id=%s"""
                cursor.execute(event_query, (username, user_id, user_id))
                event_id = cursor.lastrowid

                # Automatically store customer information when booking an event
                user_email_query = """SELECT email FROM users WHERE username=%s"""
                cursor.execute(user_email_query,(session['username'],))
                user_email=cursor.fetchone() 
                
                if user_email is not None:
                    email=user_email[0]
                    
                    customer_query = """INSERT INTO customers (name,email,event_id) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE name=%s, email=%s, event_id=%s"""
                    cursor.execute(customer_query, (session['username'], email, event_id, session['username'], email, event_id)) 
                    connection.commit()

                connection.commit()  # Commit all changes

                return redirect(url_for('login'))

            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")
            finally:
                cursor.close()
                connection.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        

        connection = create_connection()

        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                # Check for valid user credentials
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()

                if user:
                    session['username'] = user['username'] 
                    session['role'] = user['role'] 
                    flash("Login successful!", "success")

                    if user['role'] == 'admin':  
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('user_dashboard'))  

                flash("Invalid username or password.", "error")

            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")

            finally:
                cursor.close()
                connection.close()

    return render_template('login.html')


@app.route('/user-dashboard')
def user_dashboard():
    
    return render_template('user_dashboard.html')

@app.route('/event-handling')
def event_handling():
    
    if 'username' in session:
        connection = create_connection()
        
        events_data = [] 

        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM events") 
            events_data = cursor.fetchall()  
            
            cursor.close()
            connection.close()

        return render_template('event_handling.html', events=events_data)  
    else:
        flash("You are not authorized to access this page.", "error")
        return redirect(url_for('login'))


# Customer Management Page Route
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']

        # Insert customer information into the database
        connection = create_connection()

        if connection:
            try:
                cursor = connection.cursor()
                insert_query = """INSERT INTO customers (name, email, phone, address) VALUES (%s,%s,%s,%s)"""
                cursor.execute(insert_query, (name,email ,phone ,address))
                connection.commit()
                flash("Customer added successfully!", "success")

            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")

            finally:
                cursor.close()
                connection.close()

    # Fetch all customers from the database for display
    customers_data = []
    connection = create_connection()
    
    if connection:
      try:
          cursor=connection.cursor(dictionary=True)
          cursor.execute("SELECT * FROM customers") 
          customers_data=cursor.fetchall() 
      finally:
          cursor.close()
          connection.close()

    
    return render_template('customers.html', customers=customers_data)



# Event Details Page
@app.route('/event_details', methods=['GET', 'POST'])
def event_details():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        organizer_name = request.form.get('organizer_name')
        address = request.form.get('address')
        event_description = request.form.get('event_description')
        location = request.form.get('location')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        event_type = request.form.get('event_type')

        # Check if all required fields are filled
        if not all([event_name, organizer_name, address, event_description, location, start_time, end_time, event_type]):
            flash("All fields are required.", "error")
            return render_template('event_details.html')

        # Insert the new event into the database
        connection = create_connection()
        
        if connection:
            try:
                cursor = connection.cursor()
                insert_query = """INSERT INTO events (event_name, organizer_name, address, event_description, location, start_time, end_time, event_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(insert_query, (event_name, organizer_name, address, event_description, location, start_time, end_time, event_type))
                connection.commit()

                event_id = cursor.lastrowid

                # Retrieve user_id for the organizer's name
                user_id_query = """SELECT id FROM users WHERE username=%s"""
                cursor.execute(user_id_query, (organizer_name,))
                user_id_result = cursor.fetchone()

                if user_id_result is not None:
                    user_id = user_id_result[0]

                    # Automatically store customer information when booking an event
                    user_email_query = """SELECT email FROM users WHERE username=%s"""
                    cursor.execute(user_email_query,(session['username'],))
                    user_email=cursor.fetchone() 
                    
                    if user_email is not None:
                        email=user_email[0]
                        
                        customer_query = """INSERT INTO customers (name,email,event_id,user_id) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE name=%s, email=%s, event_id=%s, user_id=%s"""
                        cursor.execute(customer_query, (session['username'], email, event_id, user_id,session['username'], email, event_id, user_id)) 
                        connection.commit()
                        

                    flash("Event registered successfully!", "success")
                    return redirect(url_for('ticket_booking'))  # Redirect to book tickets page
                else:
                    flash("Organizer not found.", "error")

            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")
            
            finally:
                cursor.close()
                connection.close()

    return render_template('event_details.html')

@app.route('/ticket_booking', methods=['GET', 'POST'])
def ticket_booking():
    if request.method == 'POST':
        try:
            
            ticket_name = request.form['ticket_name']
            quantity = int(request.form['quantity'])
            event_type = request.form['event_type']
            # cash_payment = request.form['cash_payment']
            customer_name = request.form['customer_name']
            ticket_class = request.form['ticket_class']
            bank_name = request.form['bank_name']
            card_type = request.form['card_type']
            cvv_number = request.form['cvv_number']

            # Print collected data for debugging
            print("Inserting into tickets:", ticket_name, quantity, event_type,  customer_name, ticket_class, bank_name, card_type, cvv_number)

            # Insert into database
            connection = create_connection()
            if connection is None:
                flash("Failed to connect to the database.", "error")
                return render_template('ticket_booking.html')

            cursor = connection.cursor()
            insert_query = """INSERT INTO tickets (ticket_name, quantity, event_type, customer_name, ticket_class, bank_name, card_type, cvv_number) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
            cursor.execute(insert_query, (ticket_name, quantity, event_type,  customer_name, ticket_class, bank_name, card_type, cvv_number))
            
            connection.commit()  # Ensure changes are committed
            flash("Ticket booked successfully!", "success")
            return redirect(url_for('halls'))  # Ensure 'halls' is a valid route

        except Exception as e:
            flash(f"Error during ticket booking: {str(e)}", "error")
            print(f"Error: {e}")  # Log the error to console
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    return render_template('ticket_booking.html')


# Admin Dashboard Route
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')
    


@app.route('/control-room')
def controlroom():
    # Fetch customers from the database
    connection = create_connection()
    cur = connection.cursor(dictionary=True)
    
    # Fetch all customers
    cur.execute("SELECT * FROM customers")
    customers = cur.fetchall()  # Ensure this returns a list of customer records
    
    # Fetch all halls
    cur.execute("SELECT * FROM halls")
    halls = cur.fetchall()  # Fetch all rows from the executed query
    
    # Check if halls_data is empty
    print("Halls Data:", halls)
    
    # Close cursor and connection
    cur.close()
    connection.close()

    
    return render_template('controlroom.html', customers=customers, halls=halls)

import logging

@app.route('/send-reminder', methods=['POST'])
def send_reminder():
    try:
        customer_id = request.form.get('id')
        message = request.form.get('message')

        # Validate inputs
        if not customer_id or not message:
            flash("Customer ID and message are required.", "error")
            return redirect(url_for('controlroom'))

        # Ensure customer_id is an integer
        try:
            customer_id = int(customer_id)
            if customer_id <= 0:
                raise ValueError("Customer ID must be a positive integer.")
        except ValueError as ve:
            flash(str(ve), "error")
            return redirect(url_for('controlroom'))

        with create_connection() as connection:
            if not connection:
                flash("Database connection failed.", "error")
                return redirect(url_for('controlroom'))

            with connection.cursor() as cursor:
                # Fetch both user_id and event_id in one query
                cursor.execute("SELECT user_id, event_id FROM customers WHERE id = %s", (customer_id,))
                customer_data = cursor.fetchone()

                if not customer_data:
                    flash(f"Customer '{customer_id}' not found.", "error")
                    return redirect(url_for('controlroom'))

                user_id, event_id = customer_data  # Unpack directly

                if event_id is None:
                    flash(f"No associated event found for customer '{customer_id}'.", "error")
                    return redirect(url_for('controlroom'))

                timestamp = datetime.datetime.now()

                # Step 3: Insert notification into the database
                query = """INSERT INTO notifications(user_id, event_id, message, timestamp) VALUES (%s, %s, %s, %s)"""
                
                cursor.execute(query, (user_id, event_id, message, timestamp))
                
            connection.commit()
            flash("Notification sent successfully!", "success")

    except Exception as e:
        logging.error(f"Error sending notification: {e}")  # Log the error
        flash(f"Error sending notification: {str(e)}", "error")

    return redirect(url_for('controlroom'))


@app.route('/send_notification/<string:event_name>', methods=['POST'])
def send_notification(event_name):
    connection = create_connection()

    if connection:
        cursor = connection.cursor(dictionary=True)

        try:
            # Step 1: Fetch the target username from the form
            target_username = request.form.get('username')  # This is the recipient username
            app.logger.info(f"Target username from form: {target_username}")

            if not target_username:
                flash("Recipient username is required to send a notification.", "error")
                return redirect(url_for('admin_dashboard'))

            # Step 2: Fetch the target user's ID
            cursor.execute("SELECT id FROM users WHERE username = %s", (target_username,))
            recipient_user = cursor.fetchone()
            app.logger.info(f"Fetched recipient user: {recipient_user}")

            if not recipient_user:
                flash(f"User '{target_username}' not found.", "error")
                return redirect(url_for('admin_dashboard'))

            recipient_user_id = recipient_user['id']
            app.logger.info(f"Using recipient user_id: {recipient_user_id}")

            # Step 3: Fetch event ID
            cursor.execute("SELECT id FROM events WHERE event_name = %s", (event_name,))
            event = cursor.fetchone()
            
            app.logger.info(f"Fetched event: {event}")
            
 
            if not event:
                flash(f"Event '{event_name}' not found.", "error")
                return redirect(url_for('admin_dashboard'))

            event_id = event['id']
            

            # Step 4: Insert notification
            message = f"Dear {target_username} , Subject : Setting an Appointment  -  I kindly request you to contact 1234567891 by 5:00 PM tomorrow to discuss regarding {event_name}.Thank you for your co-operation!"
            insert_query = """INSERT INTO notifications (user_id, message, event_id) VALUES (%s, %s, %s)"""
            app.logger.info(f"Inserting notification: user_id={recipient_user_id}, event_id={event_id}, message={message}")

            cursor.execute(insert_query, (recipient_user_id, message, event_id))
            update_status_query = """UPDATE events SET status = 'Confirmed' WHERE id = %s"""
            cursor.execute(update_status_query, (event_id,))
            # Commit transaction
            connection.commit()
            flash(f"Notification sent to {target_username} for Event: {event_name}.", "success")

        except Exception as e:
            # Log the error for debugging
            app.logger.error(f"Error in send_notification: {e}")
            flash(f"An error occurred: {e}", "error")

        finally:
            # Ensure resources are cleaned up
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/notifications', endpoint='notifications')  # Explicit endpoint name for clarity
def notifications():
    if 'username' not in session:
        flash("You are not authorized to access this page.", "error")
        return redirect(url_for('login'))
    if session.get('username') == "admin":
        flash("You are not authorized to access this page.", "error")
        return redirect(url_for('login'))

    print(f"Session username: {session.get('username')}")  # Debugging

    connection = create_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        # Fetch user ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user = cursor.fetchone()

        if not user:
            flash("User not found.", "error")
            return redirect(url_for('login'))

        user_id = user['id']
        print(f"User ID: {user_id}")  # Debugging

        # Fetch notifications from `notifications` table
        cursor.execute("""
            SELECT 
                n.message, 
                e.event_name, 
                n.timestamp, 
                n.notification_type, 
                n.is_read, 
                n.acknowledged 
            FROM notifications n
            JOIN events e ON n.event_id = e.id
            WHERE n.user_id = %s
            ORDER BY n.timestamp DESC
        """, (user_id,))
        notifications = cursor.fetchall()


        print(f"Fetched notifications: {notifications}")  
        return render_template('notifications.html', notifications=notifications)

    except Exception as e:
        print(f"Error: {e}")
        flash(f"An error occurred: {e}", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template('notifications.html', notifications=[])


# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'srichandanak.24@gmail.com'  
app.config['MAIL_PASSWORD'] = 'uteu nbjt dmch lzom'      # app password generated from Google
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)
s = URLSafeTimedSerializer('Thisisasecret!')  # Secret key for token 

@app.route('/send-email', methods=['POST'])
def send_email():
    subject = request.form.get('subject')
    recipient = request.form.get('recipient')
    body = request.form.get('body')

    if not (subject and recipient and body):
        return "Invalid request. Please provide subject, recipient, and body parameters."

    msg = Message(subject=subject,sender=app.config['MAIL_USERNAME'],recipients=[recipient])
    msg.body = body

    try:
        mail.send(msg)
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


# Logout Route
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Check if the email exists in the database
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                # Generate an OTP (One-Time Password)
                otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
                
                # Store OTP in session for verification later
                session['otp'] = otp
                session['otp_email'] = email
                
                # Send OTP via email
                msg = Message('Password Reset Request',
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[email])
                msg.body = f'Your OTP for password reset is {otp}'
                mail.send(msg)
                
                flash('Check your email for the OTP to reset your password.', 'info')
                return redirect(url_for('verify_otp'))  # Redirect to OTP verification page
            else:
                flash('Email not found.', 'error')

            cursor.close()
            connection.close()
    
    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        
        if entered_otp and int(entered_otp) == session.get('otp'):
            return redirect(url_for('reset_password'))  # Redirect to reset password page
        else:
            flash('Invalid OTP. Please try again.', 'error')

    return render_template('verify_otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        
        # Update the user's password in the database
        email = session.get('otp_email')  # Get email from session
        
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Your password has been updated!', 'success')
            return redirect(url_for('login'))  # Redirect to login page after resetting

    return render_template('reset_password.html')

@app.route('/halls', methods=['GET', 'POST'])
def halls():
    if request.method == 'POST':
        # Retrieve form data
        hall = request.form.get('hall')
        attendees = request.form.get('attendees')
        food = request.form.get('food')
        tech = request.form.getlist('tech[]')  # For multiple checkbox selections
        setup = request.form.getlist('setup[]')  # For setup requirements
        av = request.form.getlist('av[]')  # For audio/visual requirements
        parking = request.form.get('parking')  # For parking requirements
        artistic = request.form.get('artistic')

        # Validate and process the form data
        if not hall or not attendees or not food:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('halls'))

        # Establish a connection to the database
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            insert_query = """INSERT INTO halls (hall, attendees, food, tech, setup, av, parking, artistic, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())"""
            cursor.execute(insert_query, (hall, attendees, food, ','.join(tech), ','.join(setup), ','.join(av), parking, artistic))
            connection.commit()
            cursor.close()
            connection.close()

            flash("Ticket booked successfully!", "success")
            return redirect(url_for('user_dashboard'))  # Redirect after successful booking

    # If GET request, just render the form
    return render_template('halls.html')

@app.route('/ticket_booking1')
def ticket_booking1():
    connection = create_connection()
    events = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)  # Use dictionary cursor
            cursor.execute("""
                SELECT event_name, organizer_name, location, address, event_description, start_time,  end_time, event_type FROM events where status = 'Confirmed' """)
            events = cursor.fetchall()  # This will now return a list of dictionaries
            print("Events fetched:", events)  # Debugging: Print the events
        except Exception as e:
            flash(f"Error fetching events: {e}", "error")
        finally:
            cursor.close()
            connection.close()

    return render_template('ticket_booking1.html', events=events)

@app.route('/book_ticket', methods=['GET', 'POST'])
def book_ticket():
    if request.method == 'POST':
        print("Book ticket route accessed")  # Debugging statement
        event_id = request.form.get('event_id')
        amount = request.form.get('amount')

        # Validate input
        if not event_id or not amount or float(amount) <= 0:
            flash("Invalid event ID or amount.", "error")
            return redirect(url_for('ticket_booking1'))

        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())

        # Prepare data for PhonePe payment
        phonepe_data = {
            "merchantId": "YOUR_MERCHANT_ID",
            "transactionId": transaction_id,
            "amount": amount,
            "callbackUrl": f"{request.url_root}callback",
            "currency": "INR",
            "paymentType": "QRCODE"
        }

        # Make a POST request to PhonePe API
        response = requests.post("https://api.phonepe.com/apis/hermes/pg/v1/pay", json=phonepe_data)

        if response.status_code == 200:
            payment_url = response.json().get('data').get('instrumentResponse').get('redirectInfo').get('url')
            return redirect(payment_url)
        else:
            flash(f"Payment initiation failed with status code: {response.status_code}", "error")
            return redirect(url_for('ticket_booking1'))

    return render_template('ticket_booking1.html')

    

@app.route('/callback', methods=['POST'])
def callback():
    # Handle the callback from PhonePe after payment completion
    data = request.json
    # Process the response here (e.g., verify payment status)
    return "Callback received", 200


if __name__ == '__main__':
    app.run(debug=True)

