from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from flask_mysqldb import MySQL
from flask_mail import Mail,Message
import MySQLdb 

 # Add this import for error handling
 

# Initialize Flask app
app = Flask(__name__)
app.config['MAIL_DEBUG'] = True
app.config['MAIL_TIMEOUT'] = 60
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 465 # Typical port for TLS
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'gompa.devi1999@gmail.com'  # Your email username
app.config['MAIL_PASSWORD'] = 'ggbaxtfabdorhayg'# Your email password (it is recommended to use environment variables for sensitive data)
app.config['MAIL_DEFAULT_SENDER'] = 'gompa.devi1999@gmail.com'  # Your email
mail = Mail(app)

# MySQL Database connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'hello'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Route for the home page (Login page)
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username and password are correct
        cursor = mysql.connection.cursor()
        try:
            # Check if it's an admin login
            cursor.execute("SELECT * FROM admin WHERE username = %s AND password = %s", (username, password))
            admin = cursor.fetchone()

            if admin:
                # Correct admin login, store user role and redirect to admin page
                session['user_role'] = 'admin'  # Set the session to admin role
                session['username'] = username  # Store username in session
                return redirect(url_for('adminpage'))  # Redirect to admin page

            # If not an admin, check for normal user
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()

            if user:
                # Correct user login, store user role and redirect to book ticket page
                session['user_role'] = 'user'  # Set the session to user role
                session['username'] = username  # Store username in session
                session['user_email'] = user['email']
                session['user_id'] = user['id']  # Store user_id in session
                return redirect(url_for('events'))  # Redirect to book ticket page

            else:
                # Incorrect login for both admin and user, show error message
                flash('Invalid username or password!', 'danger')
                return redirect(url_for('home'))  # Stay on the home page for retry

        except MySQLdb.Error as err:  # Use MySQLdb.Error instead of mysql.connector.Error
            print("Error:", err)
            return "Error during login", 500
        finally:
            cursor.close()

    return render_template('index.html')  # Always render the login page (index.html)

@app.route('/admin/view_hall_bookings', methods=['GET', 'POST'])
def view_hall_bookings():
    if session.get('user_role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT hb.id AS booking_id, hb.name, hb.location, hb.start_time, hb.end_time, 
                   hb.description, hb.email AS user_email, u.id AS user_id, hb.hall_capacity, 
                   p.cash_payment, p.ticket_class, p.bank_name, p.card_type, p.created_at
            FROM hall_bookings hb
            LEFT JOIN payments p ON hb.id = p.booking_id
            LEFT JOIN users u ON hb.user_id = u.id  -- Assuming user_id is a foreign key in hall_bookings
        """)
        hall_bookings = cursor.fetchall()
    except MySQLdb.Error as err:
        print("Error:", err)
        flash("Error fetching hall bookings and payment details: " + str(err), "danger")
        hall_bookings = []
    finally:
        cursor.close()

    return render_template('view_hall_bookings.html', hall_bookings=hall_bookings)


@app.route('/admin/send_appointment_email/<int:booking_id>', methods=['POST'])
def send_appointment_email(booking_id):
    appointment_date = request.form['appointment_date']
    
    # Fetch the booking details and user email based on booking_id
    cursor = mysql.connection.cursor()
    try:
        # Query to get booking details along with the user's email from hall_bookings table
        cursor.execute("""
            SELECT hb.name, hb.location, hb.start_time, hb.end_time, hb.email
            FROM hall_bookings hb
            WHERE hb.id = %s
        """, (booking_id,))
        booking_details = cursor.fetchone()

        # Debugging: Print the result of the query to check what was fetched
        print(f"Booking details for booking_id {booking_id}: {booking_details}")
        
        if booking_details:
            # Extract the booking details
            user_email = booking_details['email']  # Directly from hall_bookings
            event_name = booking_details['name']
            location = booking_details['location']
            start_time = booking_details['start_time']
            end_time = booking_details['end_time']

            # If no email is found for the booking, return an error
            if not user_email:
                flash("User email not found for this booking.", "danger")
                return redirect(url_for('view_hall_bookings'))  # Redirect if no email is found

            # Send the email with the appointment details
            msg = Message("Your Appointment Date for " + event_name,
                          recipients=[user_email])  # Correct recipient setup
            msg.body = f"""
            Dear User,

            Your appointment for the event '{event_name}' has been scheduled.

            Event Name: {event_name}
            Location: {location}
            Start Time: {start_time}
            End Time: {end_time}

            Your appointment date is: {appointment_date}

            Thank you for choosing our service!

            Regards,
            Admin
            """
            mail.send(msg)

            flash("Appointment email sent successfully!", "success")
        else:
             flash("Booking not found for this ID.", "danger")
    except MySQLdb.Error as err:
        flash(f"Error sending email: {err}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('view_hall_bookings'))

@app.route('/admin/send_notification/<int:booking_id>', methods=['POST'])
def send_notification(booking_id):
    notification_text = request.form['notification_text']
    
    # Fetch the user ID and other details based on the booking_id
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT hb.user_id, hb.name
            FROM hall_bookings hb
            WHERE hb.id = %s
        """, (booking_id,))
        booking_details = cursor.fetchone()

        if booking_details:
            user_id = booking_details['user_id']
            

            # Insert the notification into the database
            cursor.execute("""
                INSERT INTO notifications (user_id, booking_id, notification_text)
                VALUES (%s, %s, %s)
            """, (user_id, booking_id, notification_text))
            mysql.connection.commit()

            # Optionally: Send a message to the user email
            # msg = Message("New Notification from Admin", recipients=[user_email])
            # msg.body = notification_text
            # mail.send(msg)

            flash("Notification sent successfully!", "success")
        else:
            flash("Booking not found for this ID.", "danger")
    except MySQLdb.Error as err:
        flash(f"Error sending notification: {err}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('view_hall_bookings'))

@app.route('/get_notifications', methods=['GET'])
def get_notifications():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return jsonify([])  # Return an empty list if the user is not logged in

    user_id = session['user_id']  # Fetch the user_id from the session
    cursor = mysql.connection.cursor()

    try:
        # Query to get the unread notifications for the logged-in user
        cursor.execute("""
            SELECT n.id, n.notification_text
            FROM notifications n
            WHERE n.user_id = %s AND n.is_read = 0
            ORDER BY n.date_sent DESC
        """, (user_id,))

        # Fetch the results and return them in a JSON response
        notifications = cursor.fetchall()

        # Format the data as a list of dictionaries
        notification_data = [{'id': n[0], 'notification_text': n[1]} for n in notifications]
        
        return jsonify(notification_data)
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        cursor.close()  # Always close the cursor after use

@app.route('/events')
def events():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("Please log in to view your notifications.", "danger")
        return redirect(url_for('home'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    try:
        # Fetch unread notifications for the logged-in user
        cursor.execute("""
            SELECT n.id, n.notification_text, n.date_sent
            FROM notifications n
            WHERE n.user_id = %s AND n.is_read = 0
            ORDER BY n.date_sent DESC
        """, (user_id,))
        
        notifications = cursor.fetchall()
    except MySQLdb.Error as err:
        print("Error fetching notifications:", err)
        notifications = []
    finally:
        cursor.close()

    return render_template('events.html', notifications=notifications)


@app.route('/book_hall', methods=['GET', 'POST'])
def book_hall():
    if 'user_id' not in session:
        flash("Please log in to book a hall.", "warning")
        return redirect(url_for('home'))  # Redirect to home page if not logged in
    
    # Print user_id from session for debugging
    print(f"User ID in session: {session.get('user_id')}")  # Check session data

    if request.method == 'POST':
        # Capture booking details from the form
        name = request.form['name']
        location = request.form['location']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        description = request.form['description']
        event_type = request.form['event_type']
        email = request.form['email']
        hall_capacity = request.form['hall_capacity']

        user_id = session['user_id']  # Get the logged-in user's ID from the session

        cursor = mysql.connection.cursor()
        try:
            # Insert booking details into the hall_bookings table, including user_id
            cursor.execute("""
                INSERT INTO hall_bookings (name, location, start_time, end_time, description, event_type, email, hall_capacity, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, location, start_time, end_time, description, event_type, email, hall_capacity, user_id))
            mysql.connection.commit()

            # Store booking details in session
            booking_id = cursor.lastrowid  # Get the last inserted booking ID
            session['booking_details'] = {
                'booking_id': booking_id,
                'name': name,
                'location': location,
                'start_time': start_time,
                'end_time': end_time,
                'description': description,
                'event_type': event_type,
                'email': email,
                'hall_capacity': hall_capacity
            }

            return redirect(url_for('payment'))  # Redirect to the payment page
        except MySQLdb.Error as err:
            flash(f"Error while booking: {err}", 'danger')
        finally:
            cursor.close()

    return render_template('book_hall.html')  # Your booking form template

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'booking_details' not in session:
        flash("No booking found. Please start from booking the hall.", "danger")
        return redirect(url_for('book_hall'))  # Redirect to book hall if no booking details found in session

    booking_details = session['booking_details']  # Retrieve booking details from session

    if request.method == 'POST':
        cash_payment = request.form['cash_payment']
        ticket_class = request.form['ticket_class']
        bank_name = request.form.get('bank_name', None)
        card_type = request.form.get('card_type', None)

        # Insert payment details into the payments table
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO payments (booking_id, cash_payment, ticket_class, bank_name, card_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (booking_details['booking_id'], cash_payment, ticket_class, bank_name, card_type))
            mysql.connection.commit()

            # Clear booking details after successful payment
            session.pop('booking_details', None)

            flash("Payment successful. Your booking is confirmed!", "success")
            
            # Ensure the redirect to the home page after payment is processed
            return redirect(url_for('home'))  # Redirect to home page after successful payment

        except MySQLdb.Error as err:
            flash(f"Error processing payment: {err}", 'danger')
        finally:
            cursor.close()

    return render_template('payment_form.html', booking_details=booking_details)  # Render the payment form



# Route for displaying new events
@app.route('/new_events')
def new_events():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM aevent")  # Fetch all created events
        events = cursor.fetchall()
    except MySQLdb.Error as err:
        print("Error:", err)
        flash("Error fetching events: " + str(err), "danger")
        events = []
    finally:
        cursor.close()

    return render_template('new_events.html', events=events)  # Show events in a list

@app.route('/adminpage', methods=['GET'])
def adminpage():
    # Check if the user is logged in as admin
    if session.get('user_role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('home'))
    
    return render_template('adminpage.html')

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    # Check if the user is logged in as admin
    if session.get('user_role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Capture form data for event creation
        event_name = request.form['event_name']
        event_location = request.form['event_location']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        available_tickets = request.form['available_tickets']
        ticket_price = request.form['ticket_price']

        # Insert the event into the 'aevent' table in the database
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO aevent (name, location, start_time, end_time, available_tickets, ticket_price)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (event_name, event_location, start_time, end_time, available_tickets, ticket_price))

            mysql.connection.commit()
            flash("Event created successfully!", "success")
            return redirect(url_for('adminpage'))  # Redirect to admin page after successful event creation
        except Exception as e:
            flash(f"Error creating event: {str(e)}", "danger")
            mysql.connection.rollback()  # Rollback in case of error
        finally:
            cursor.close()

    return render_template('create_event.html')

@app.route('/book_ticket/<int:event_id>', methods=['GET'])
def book_ticket(event_id):
    # Fetch event details by event_id
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM aevent WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()
    cursor.close()

    if not event:
        flash("Event not found", "danger")
        return redirect(url_for('new_events'))  # Redirect to events list if event not found

    return render_template('book_ticket.html', event=event)

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    user_id = session.get('user_id')  # Ensure user_id is retrieved from session
    if not user_id:
        flash("You must be logged in to book a ticket.", "danger")
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    event_id = request.form['event_id']
    num_tickets = int(request.form['num_tickets'])

    # Fetch event details to update available tickets and price
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM aevent WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()

    if not event:
        flash("Event not found", "danger")
        return redirect(url_for('new_events'))  # Redirect to events list if event not found

    available_tickets = event['available_tickets']
    ticket_price = event['ticket_price']

    # Check if there are enough tickets available
    if num_tickets > available_tickets:
        flash("Not enough tickets available", "danger")
        return redirect(url_for('book_ticket', event_id=event_id))  # Go back to booking page

    # Insert booking details into the ticket_booking table
    cursor.execute("""
        INSERT INTO ticket_booking (event_id, num_tickets, ticket_price, user_id)
        VALUES (%s, %s, %s, %s)
    """, (event_id, num_tickets, ticket_price, user_id))

    # Update the available tickets in the aevent table
    new_available_tickets = available_tickets - num_tickets
    cursor.execute("""
        UPDATE aevent
        SET available_tickets = %s
        WHERE event_id = %s
    """, (new_available_tickets, event_id))

    mysql.connection.commit()
    cursor.close()

    flash("Booking confirmed!", "success")
    return redirect(url_for('new_events'))  # Redirect back to the events list

# Route for viewing ticket bookings (only for admin)
@app.route('/admin/view_ticket_bookings')
def view_ticket_bookings():
    if session.get('user_role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('home'))  # Redirect to the login page if not admin

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT tb.id AS booking_id, tb.event_id, tb.num_tickets, tb.ticket_price, 
                   tb.booking_time, e.name AS event_name, u.username AS user_name
            FROM ticket_booking tb
            JOIN aevent e ON tb.event_id = e.event_id
            JOIN users u ON tb.user_id = u.id
        """)
        bookings = cursor.fetchall()

    except MySQLdb.Error as err:
        print("Error:", err)
        flash(f"Error fetching ticket bookings: {err}", "danger")
        bookings = []
    finally:
        cursor.close()

    return render_template('view_ticket_bookings.html', bookings=bookings)

# ROUTE FORADMIN VIEW REGISTRATIONS 
@app.route('/admin/view_registrations')
def view_registrations():
    if session.get('user_role') != 'admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('home'))  # Redirect to the login page if not admin

    cursor = mysql.connection.cursor()
    try:
        # Fetch all registrations from the 'users' table
        cursor.execute("SELECT username, email, mobile_number, city, state FROM users")
        registrations = cursor.fetchall()  # Fetch all user records

    except MySQLdb.Error as err:
        print("Error:", err)
        flash(f"Error fetching registrations: {err}", "danger")
        registrations = []  # If there's an error, set registrations to an empty list
    finally:
        cursor.close()

    # Render the view_registrations page and pass the registrations data to the template
    return render_template('view_registrations.html', registrations=registrations)


# Route for user registration (Separate from login)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        repassword = request.form['repassword']
        email = request.form['email']
        mobile_number = request.form['mobile']
        city = request.form['city']
        state = request.form['state']

        # Check if passwords match
        if password != repassword:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Store user in the database
        cursor = mysql.connection.cursor()

        try:
            cursor.execute(""" 
                INSERT INTO users (username, password, email, mobile_number, city, state) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, password, email, mobile_number, city, state))

            mysql.connection.commit()
            flash("Registration successful! Please login.", "success")
        except MySQLdb.Error as err:
            print("Error:", err)
            flash("Error registering user: " + str(err), 'danger')
            return redirect(url_for('register'))  # Stay on registration page if error
        finally:
            cursor.close()

        return redirect(url_for('home'))  # Redirect to login page after successful registration

    return render_template('register.html')  # User registration page


# Route for logout
@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))  # Redirect to the login page


if __name__ == '__main__':
    app.secret_key = '123456'  # Set a secret key for session management
    app.run(debug=True)
