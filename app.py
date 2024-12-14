#import necessary libs and dependencies for app functionality
from flask import Flask, render_template, request, redirect ,session, url_for, flash, jsonify
from dotenv import load_dotenv
import os
import csv
import uuid
from math import radians,sin,cos,sqrt,atan2
from datetime import datetime, timedelta
from html import escape
import hashlib

# Load environment variables from .env
load_dotenv()

#create flask app
app = Flask(__name__)

#set secret key for session management
app.secret_key = os.getenv('SECRET_KEY')

#define hourly wage
employee_hourly_wage = 22

#WORK LOCATION COORDINATES AND RADIUS ALLOWED
MERCY_UNIV_LAT =  41.0165728
MERCY_UNIV_LON =  -73.8610076
ALLOWED_RADIUS_KM = 2

#req to meet vacation hours
# vacation_hours_required = .02

#Location validation function
def haversine(lat1, lon1, lat2, lon2):
    #radius of earth in km
    R = 6371

    #convert latitude difference to radians
    dlat = radians(lat2 - lat1) 

    #convert longitude difference to radians
    dlon = radians(lon2 - lon1)

    #square of half the chord length btw two points
    a = sin(dlat / 2 ) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2

    #compute angular distance in radians btw two points
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    #return angular distance * earths radius to get great circle distance in km
    return R * c

def calculate_earnings(clock_in_times):
    total_seconds = 0
    for in_time, out_time in clock_in_times:
        # If the input is a string, convert it to a datetime object
        if isinstance(in_time, str):
            in_time = datetime.strptime(in_time, "%Y-%m-%d %H:%M:%S")
        if isinstance(out_time, str) and out_time:
            out_time = datetime.strptime(out_time, "%Y-%m-%d %H:%M:%S")
        
        # Only calculate if both in_time and out_time are valid
        if in_time and out_time:
            total_seconds += (out_time - in_time).total_seconds()
    
    total_hours = total_seconds / 3600
    return round(total_hours * employee_hourly_wage, 2)

#retrieving employee data
def get_employee_files(employee_id):
    return {
        "clock_data": f"data/{employee_id}_clock.csv",
    }

#HOME PAGE
@app.route('/')
def home():
    return render_template('home.html')

#CREATE ACCOUNT PAGE
@app.route('/create_account', methods=['GET','POST'])
def create_account():
    if request.method == 'POST':
        name = escape(request.form['name'])
        email = escape(request.form['email'])
        password = request.form['password']
        dob = escape(request.form['dob'])
        employee_id = f"E{uuid.uuid4().hex[:8]}"
        
        # Hash the password with hashlib
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        #Ensure employee_data.csv exists with headers
        if not os.path.exists('employee_data.csv'):
            with open('employee_data.csv', 'w', newline='') as file:
                writer = csv.DictWriter(file,fieldnames=['name','email','password','dob','employee_id'])
                writer.writeheader()
        
        #Append the new employee data to employee_data.csv
        with open('employee_data.csv', 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['name', 'email', 'password', 'dob', 'employee_id'])
            writer.writerow({'name': name, 'email': email, 'password': hashed_password, 'dob': dob, 'employee_id': employee_id})
        
        #Ensure the 'data/' directory exists for individual files
        if not os.path.exists('data'):
            os.makedirs('data')

        #create individual files for employees
        employee_files = get_employee_files(employee_id)
        with open(employee_files['clock_data'], 'w', newline='') as clock_file:
            clock_writer = csv.DictWriter(clock_file,fieldnames=['date', 'clock_in', 'clock_out'])
            clock_writer.writeheader()

        flash("Account created sucessfully! Please log in.")
        return redirect(url_for('login'))
    return render_template('create_account.html')

#LOGIN PAGE
@app.route('/login', methods = ['GET','POST'])
def login():
    if request.method == 'POST':
        #GET FORM DATA
        email = escape(request.form['email'])
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()


        #Capture user's latitude and longitude from form
        try:
            user_lat = float(request.form['latitude']) #add hidden input
            user_lon = float(request.form['longitude'])
        except ValueError:
            flash("Unable to capture location. Please enable location services.")
            return redirect(url_for("login"))
               
        #calculate distance using haversine formula
        distance = haversine(user_lat,user_lon,MERCY_UNIV_LAT,MERCY_UNIV_LON)

        #Check is user is within allowed distance
        if distance > ALLOWED_RADIUS_KM:
            flash("Login allowed only from within 2 km of Mercy Univeristy's Dobbs Ferry Campus")
            return(redirect(url_for("login")))
        
        #check if email exists and verify password


        with open('employee_data.csv', 'r') as file:
            reader = csv.DictReader(file)
            found_email = False  # Flag to track if email is found
            
            for row in reader:
                if email == row['email']:
                    found_email = True  # Email exists in CSV
                    if hashed_password == row['password']:
                        session.clear()  # Clear any previous session data
                        session['employee_id'] = row['employee_id']
                        session['name'] = row['name']
                        flash('Login successful!')
                        return redirect(url_for('dashboard'))
                    else:
                         # Email exists but password is incorrect
                           flash("Invalid password.")
                           return redirect(url_for('login'))
            
            if not found_email:
                flash("Invalid email.")
                return redirect(url_for('login'))

       

    #If GET request, render login form
    return render_template('login.html')


#DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'employee_id' not in session:
        flash("You need to log in first.")
        return(redirect(url_for('login')))
    
    employee_files = get_employee_files(session['employee_id'])
    earnings = session.pop('earnings', 0) 
    clock_in_times = [ ]

    try:
        #use dictreader to parse csv data into dictionaries
        with open(employee_files['clock_data'], 'r') as clock_file:
            clock_reader =  csv.DictReader(clock_file)

            #check if file is readable and not empty
            if not any(clock_reader):
                raise FileNotFoundError
            
            #reset the file pointer to the beginning, so csv.dictreader can read the entire file
            clock_file.seek(0)

            clock_in_times = []

            for row in clock_reader:
                try:
                    if row['clock_in'] == 'clock_in' or not row['clock_in']:
                        print(f"skip invalid header or header row: {row}")
                        continue

                    #parse clock in data
                    clock_in = datetime.strptime(row['clock_in'], '%Y-%m-%d %H:%M:%S')
                    
                    #parse clock out
                    clock_out = (
                        datetime.strptime(row['clock_out'], '%Y-%m-%d %H:%M:%S')
                        if row['clock_out'] else None
                    )

                except ValueError as e:
                    print(f"Error parsing row: {row} - {e}")
                    continue  # Skip this row if parsing fails
                
                #append to times to the list
                clock_in_times.append((
                    clock_in.strftime('%Y-%m-%d %H:%M:%S'),
                    clock_out.strftime('%Y-%m-%d %H:%M:%S') if clock_out else ''
                ))

    except FileNotFoundError:
        flash("Clock data file not found.")

    return render_template(
        'dashboard.html',
        name = session['name'],
        earnings = earnings,
        clock_in_times = clock_in_times,
    )

#Calculate Earnings
@app.route('/calculate_earnings', methods=['POST'])
def calculate_earnings_route():
    if 'employee_id' not in session:
        flash("You need to log in first.")
        return redirect(url_for('login'))

    employee_files = get_employee_files(session['employee_id'])

    try:
        # Process clock data to calculate earnings
        clock_in_times = []
        if 'clock_data' in employee_files:
            with open(employee_files['clock_data'], 'r') as clock_file:
                clock_reader = csv.DictReader(clock_file)

                for row in clock_reader:
                    try:
                        if row['clock_in'] and row['clock_out']:
                            clock_in = datetime.strptime(row['clock_in'], '%Y-%m-%d %H:%M:%S')
                            clock_out = datetime.strptime(row['clock_out'], '%Y-%m-%d %H:%M:%S')
                            clock_in_times.append((clock_in, clock_out))
                    except ValueError as e:
                        print(f"Error parsing row: {row} - {e}")
                        continue

        if not clock_in_times:
            flash("No completed clock-ins found.")
            return redirect(url_for('dashboard'))

        # Fetch employee's hourly wage
        earnings = calculate_earnings(clock_in_times)

        # Pass earnings back to the dashboard
        session['earnings'] = earnings  # Store in session for use in the dashboard
        flash(f"Earnings calculated successfully: ${earnings}")
        return redirect(url_for('dashboard'))

    except FileNotFoundError as e:
        flash(f"Clock data file not found: {e}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"An error occurred: {e}")
        return redirect(url_for('dashboard'))


#CLOCK IN
@app.route('/clock_in', methods=['POST'])
def clock_in():
    if 'employee_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    current_time = datetime.now()
    formatted_time  = current_time.strftime('%Y-%m-%d %H:%M:%S')
    employee_files = get_employee_files(session['employee_id'])

    with open(employee_files['clock_data'],'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames= ['date', 'clock_in', 'clock_out'])
        writer.writerow({'date': current_time.date(), 'clock_in': formatted_time, 'clock_out': ''})

    flash("Clocked in successfully!")
    return redirect(url_for('dashboard'))

#CLOCK OUT
@app.route('/clock_out', methods=['POST'])
def clock_out():
    if 'employee_id' not in session:
        return jsonify({"error":"Unauthorized"}), 401
    
    current_time = datetime.now()
    formatted_time  = current_time.strftime('%Y-%m-%d %H:%M:%S')
    employee_files = get_employee_files(session['employee_id'])

    updated_rows = []
    found_incomplete = False

    with open(employee_files['clock_data'], 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not row['clock_out']:
                row['clock_out'] = formatted_time
                found_incomplete = True
            updated_rows.append(row)
    
    if not found_incomplete:
        flash("No activate clock in record found.")
        return redirect(url_for('dashboard'))

    with open(employee_files['clock_data'], 'w', newline= '') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'clock_in', 'clock_out'])
        writer.writeheader()
        writer.writerows(updated_rows)

    flash("Clocked out sucessfully!")
    return redirect(url_for('dashboard'))

#DELETE ACCOUNT
@app.route('/delete_account', methods = ['POST'])
def delete_account():
    if 'employee_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    employee_id = session['employee_id']

    #remove employee data from main csv
    with open('employee_data.csv', 'r') as file:
        rows = [row for row in csv.DictReader(file) if row['employee_id'] != employee_id]
    
    with open('employee_data.csv', 'w',newline ='') as file:
        writer = csv.DictWriter(file, fieldnames=['name', 'email','password', 'dob', 'employee_id'])
        writer.writeheader()
        writer.writerows(rows)

    #delete individual employee files
    employee_files = get_employee_files(session['employee_id'])
    for file in employee_files.values():
        if os.path.exists(file):
            os.remove(file)
    
    session.clear()
    flash("Account deleted sucessfully!")
    return redirect(url_for('home'))

#Logout Route
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # Clear all session data
    flash("You have been logged out.")
    return redirect(url_for('home'))  # Redirect to the home or login page

if __name__ == '__main__':
    app.run(debug=True)


