from flask import Flask, render_template, redirect, request, jsonify, flash, redirect, url_for, send_from_directory, session, make_response
from flask_session import Session
import mongodb
import logging
from datetime import datetime, timedelta
import redis
import os
import pandas as pd
try:
    REDIS_HOST = os.getenv('REDIS_HOST', '')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_DB = os.getenv('REDIS_DB')
    REDIS_PORT = os.getenv('REDIS_PORT')
    url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    print(url)
    r = redis.Redis.from_url(url=url, db=0)
    r.ping()  # Test the connection
    print("Connected to Redis successfully!")
except Exception as e:
    REDIS_DB = 0
    REDIS_HOST = "localhost" 
    REDIS_PORT = 6379
    
    url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    print(url)
    print(f"Error connecting to Redis: {e}")

app = Flask(__name__)
app.config["SESSION_TYPE"] = "redis"
app.secret_key = 'abcdef'
app.config["SESSION_REDIS"] = redis.from_url(url=url)
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_FILE_DIR"] = "data/sessions"
Session(app)

from logging.handlers import TimedRotatingFileHandler

# Create two separate loggers: one for general application logs, one for error logs
app_logger = logging.getLogger('app')
error_logger = logging.getLogger('error')

# Set the logging level
app_logger.setLevel(logging.DEBUG)  # For application logs, capture DEBUG and above
error_logger.setLevel(logging.ERROR)  # For error logs, capture ERROR and above

# Create TimedRotatingFileHandler for rotating logs every day
app_file_handler = TimedRotatingFileHandler('logs/app.log', when='midnight', interval=1, backupCount=7)  # Keep 7 days of logs
error_file_handler = TimedRotatingFileHandler('logs/error.log', when='midnight', interval=1, backupCount=7)  # Keep 7 days of error logs

# Create log formats for the two loggers
app_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set the format for each handler
app_file_handler.setFormatter(app_format)
error_file_handler.setFormatter(error_format)

# Add handlers to the loggers
app_logger.addHandler(app_file_handler)
error_logger.addHandler(error_file_handler)
# Now you can use these loggers in your code

app_logger.debug(f"Seeding Mongo DB!!: {mongodb.read_and_update_from_csv()}")

from bson import ObjectId
def serialize_mongo_data(data):
    if isinstance(data, list):  # For lists of documents
        for i, doc in enumerate(data):
            if isinstance(doc, dict):  # Check if the element is a dictionary
                data[i] = serialize_mongo_data(doc)
    elif isinstance(data, dict):  # For single document
        for key, value in data.items():
            if isinstance(value, ObjectId):  # Convert ObjectId to string
                data[key] = str(value)
            elif value is None:  # Replace None with a default value (e.g., 'N/A')
                data[key] = 'N/A'
            elif isinstance(value, (dict, list)):  # Recursively serialize nested documents
                data[key] = serialize_mongo_data(value)
    return data

def convert_to_fullcalendar(data):
    events = []
    shift_colors = {
    "General-1": "#388E3C",  # Matte Forest Green
    "General-2": "#689F38",  # Subtle Olive Green
    "Morning": "#0288D1",    # Calm Matte Blue
    "Noon": "#FFA000",       # Muted Gold Amber
    "Week Off": "#E64A19",   # Warm Burnt Orange
    "Night": "#512DA8"       # Soft Royal Purple
}

    for user_data in data:
        user_name = user_data['name']
        user_team = user_data['team']
        schedule = user_data['schedule']
        
        # Loop through the schedule for each user
        for date_str, shift in schedule.items():
            # Convert the string date into a datetime object
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            color = shift_colors.get(shift, "#000000")
            # FullCalendar event structure
            event = {
                "title": f"{user_name}: {shift}",  # Shift type (e.g., 'G1', 'M', 'Week Off', etc.)
                "start": start_date.isoformat(),  # Start time
                "end": start_date.isoformat(),  # End time (same as start time for full-day events)
                "color": color,
                "allDay": True,
                "user": user_name,
                "team":user_team,
                "description":f"{user_name}-{user_team}: {shift}"
            }
            events.append(event)
    
    return events
def style_shift(shift):
    if shift == "Week Off":
        return 'style="background-color: lightgray;"'
    elif shift == "General-1":
        return 'style="background-color: lightblue;"'
    elif shift == "General-2":
        return 'style="background-color: lightgreen;"'
    elif shift == "Noon":
        return 'style="background-color: lightyellow;"'
    elif shift == "Night":
        return 'style="background-color: lightcoral;"'
    else:
        return ''


@app.errorhandler(500)
def internal_server_error(error):
    """Handles 500 errors."""
    app_logger.debug(f"500 Error - Internal server error: {str(error)}")
    return "Internal server error", 500

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    app_logger.debug("Returning to home page!!")
    return redirect(url_for("home"))


def formated_leave(user_leaves):
    formatted_events = []
    for item in user_leaves:
        if item['status'] == "pending":
            color = "cyan"  # Material Design color for pending (light teal alternative)
        elif item['status'] == 'approved':
            color = "teal"  # Material Design color for
            # approved
        else:
            color = "red"  # Material Design color for denied
        formatted_event = {
            'title': f"{item['name']}: {item['title']}:"
                     f" {item['comment']}",

            # Format the title
            'start': f"{item['start']}T00:00:00",  # Set start date in ISO format
            'end': f"{item['start']}T00:00:00",  # Set end date (same as start date for all-day events)
            'color': color,  # Set a fixed color (you can map colors as needed)
            'allDay': True,  # Make it an all-day event
            'user': item['name'],  # Add the user's name
            'team': item['team'],  # Add the team name
            'comment':item['comment'], # Add the reason
            # for leave
            'description': f"{item['name']}-"
                           f"{item['team']}: "
                           f"{item['title']} : "
                           f"{item['comment']}'"  # Set
            # description
            }
        formatted_events.append(formatted_event)
    return formatted_events


def transform_data(data):
    # print(data)
    requests = []
    color_map = {
        "Leave": "#0288D1",
        "Week Off": "#E64A19",
        "WFH": "#388E3C"
    }
    for entry in data:
        user = entry['user']
        team = entry['team']
        event = entry['event']
        date = entry['date']
        comment = entry['need']
        color = color_map.get(event,
                              "#000000")  # Default color if not found in color_map

        # Create the transformed entry
        requests.append({
            "user": user,
            "team": team,
            "option": event,
            "date": date,
            "comment": comment,
        })

    return requests



@app.route("/user_console", methods=["GET", "POST"])
def user_console():
    try:
        if request.method == "POST":
            current_date = datetime.now()
            email = request.form.get("email")
            password = request.form.get("password")
            # print("Calling mongodb")
            status, user_data = mongodb.login(email, password)
            # print("user data", user_data)
            session["password"] = password
            session["email"] = email
            name = user_data["name"]
            print(f"Session has been stored for {email}")
            app_logger.debug(f"Session has been stored for {email}:{name}")
            if status:
                managers = mongodb.get_managers() if isinstance(mongodb.get_managers(), list) else []
                app_logger.debug(f"Invoking get_managers function to get the list of managers!!")
                teams = mongodb.get_teams() if isinstance(mongodb.get_teams(), list) else []
                app_logger.debug("Invoking get_teams function to get list of teams")
                admins = mongodb.get_privilege() if isinstance(mongodb.get_privilege(), list) else []
                app_logger.debug("Invoking get_privilege function to get the admin details!!")
                holidays = mongodb.get_fullholiday_data()
                app_logger.debug("Invoking get_fullholiday_data to get all the holiday lists!!")
                pending_leaves = mongodb.get_pending_leaves()
                app_logger.debug("Invoking get_pending_leaves function to get all the pending leaves for approval!!")
                # print("pending leaves:", pending_leaves)
                pending_requests = transform_data(pending_leaves)

                # print("Pending requests:", 
                # pending_requests)
                session["pending_requests"] = pending_requests
                app_logger.debug(f"Pending leave requests has been saved in the session")
                # print("Email and password matched!!")
                calendar_events = convert_to_fullcalendar(mongodb.get_all_events())
                session["user_data"] = user_data
                # print(f"User session has been stored for
                # {user_data}")
                if user_data["privilege"] == "admin":
                    app_logger.debug("The user logged in is found to be admin!!")
                    user_leaves = mongodb.get_leaves()  
                    # print("User leaves:", user_leaves)
                    if user_leaves:               
                        formated_events = formated_leave(user_leaves)
                    else:
                        formated_events = []
                    all_calendar_events = (
                            calendar_events+formated_events+holidays)
                    # print("Formatted leaves,",
                    # formated_events)
                    team_list = serialize_mongo_data(mongodb.get_teams())
                    users_with_teams = serialize_mongo_data(mongodb.users())
                    summary_data = mongodb.summary()
                    rows = []
                    for user, details in summary_data.items():
                        for date, shift in details[
                            'schedule'].items():
                            rows.append({
                                "User ": user,
                                "Team": details['team'],
                                "Date": date,
                                "Shift": shift
                            })
                    df = pd.DataFrame(rows)
                    df_pivot = df.pivot_table(
                        index=["User ", "Team"],
                        columns="Date", values="Shift",
                        aggfunc='first')
                    df_pivot.reset_index()
                    df_html = df_pivot.to_html(
                        classes='dataframe', index=False)
                    print(df_html)
                    # print("user with teams:",
                    # users_with_teams)
                    session["team_list"] = team_list
                    session["users_with_teams"] = users_with_teams
                    session["admins"] = admins
                    session["managers"] = managers
                    session["teams"] = teams
                    session["all_calendar_events"] = all_calendar_events
                    session['summary_data'] = df_html

                    print("Executing manager console:")
                    app_logger.debug(f"Session for {team_list}, {admins}, {managers}, {teams}, {all_calendar_events} has been stored!!")
                    app_logger.debug("Logging into the manager console!!")
                    app_logger.debug("Rendering into manager_console.html!")
                    return render_template(
                        "manager_console.html",
                        managers=managers, admins=admins,
                        user=user_data, teams=team_list,
                        users=users_with_teams,
                        calendar_events=all_calendar_events, event_requests = pending_requests,schedule_data=summary_data)
                
                else:
                    app_logger.debug("The user logged in found to be a normal user!!")
                    all_user_leaves = mongodb.get_leaves()
                    holidays = mongodb.get_fullholiday_data()
                    calendar_events = convert_to_fullcalendar(mongodb.get_all_events())
                    #my_approved_events = mongodb.my_approved_events(name)
                    # print(my_approved_events)
                    print("calendar events", calendar_events)
                    if all_user_leaves:               
                        all_formated_events = formated_leave(all_user_leaves)
                    else:
                        all_formated_events = []
                    all_calendar_events = calendar_events+all_formated_events+holidays
                    try:
                        user_leaves = mongodb.get_leaves(name or [])  
                        # print("User leaves:", user_leaves)
                        if user_leaves:               
                            formated_events = formated_leave(user_leaves)
                        else:
                            formated_events = []
                        # print("Formatted leaves,",formated_events)
                        events = convert_to_fullcalendar(mongodb.get_user_events(user_data['name']) or [])
                        # print("Events for the user:", events)
                        # print("User events:",events)
                        all_events = events+formated_events+holidays
                        # print("All events:", all_events)
                        session["events"] =  events
                        aggregated_leaves = mongodb.my_approved_events(
                            name)

                        if not aggregated_leaves:
                            aggregated_leaves = {}
                        session["aggregated_leaves"] =aggregated_leaves
                        print("Aggregated leaves:",aggregated_leaves)
                        print("All events:",all_events)
                        print("All Calendar events:",all_calendar_events)
                        return render_template("user_console.html", user=user_data, events=all_events, calendar_events=all_calendar_events,aggregated_leaves=aggregated_leaves)
                    except Exception as e:
                        app_logger.debug(f"Error fetching events: {str(e)}, hence redirecting to home page")
                        flash(f"Error fetching events: {str(e)}", "danger")
                        return redirect(url_for("home"))
            app_logger.debug("Unable to login!" if status else "No account found or password mismatch!")
            flash("Unable to login!" if status else "No account found or password mismatch!")
            return redirect(url_for("home"))
        
        elif request.method == "GET":
            current_date = datetime.now()
            user_data = session.get("user_data")
            if user_data:
                if user_data["privilege"] == "admin":
                    managers = mongodb.get_managers() if isinstance(mongodb.get_managers(), list) else []
                    calendar_events = convert_to_fullcalendar(mongodb.get_all_events())
                    holidays = mongodb.get_fullholiday_data()
                    user_leaves = mongodb.get_leaves()
                    summary_data = mongodb.summary()
                    rows = []
                    for user, details in summary_data.items():
                        for date, shift in details[
                            'schedule'].items():
                            rows.append({
                                "User ": user,
                                "Team": details['team'],
                                "Date": date,
                                "Shift": shift
                            })
                    df = pd.DataFrame(rows)
                    df_pivot = df.pivot_table(
                        index=["User ", "Team"],
                        columns="Date", values="Shift",
                        aggfunc='first')
                    df_pivot.reset_index(inplace=True)
                    df_html = df_pivot.to_html(
                        classes='dataframe', index=False)
                    # print("User leaves:", user_leaves)
                    if user_leaves:               
                        formated_events = formated_leave(user_leaves)
                    else:
                        formated_events = []
                    all_calendar_events = calendar_events+formated_events+holidays
                    session["all_calendar_events"] = all_calendar_events
                    session['summary'] = df
                    team_list = session.get("team_list", [])
                    admins = session["admins"]
                    pending_leaves = mongodb.get_pending_leaves()
                    # print(pending_leaves)
                    pending_requests = transform_data(
                        pending_leaves)
                    # print(pending_requests)
                    session["pending_requests"] = pending_requests
                    session['summary_data'] = df_html
                    users_with_teams = serialize_mongo_data(mongodb.users())
                    """print("Executing manager console:")
                    print("User Data:", user_data)
                    print("Teams:",team_list)
                    print("Users with teams:", users_with_teams)
                    print("Calendar_events:",calendar_events)"""
                    return render_template(
                        "manager_console.html",
                        managers=managers,admins=admins,user=user_data, teams=team_list, users=users_with_teams, calendar_events=all_calendar_events, event_requests = pending_requests,schedule_data=summary_data)
                
                else:
                    all_user_leaves = mongodb.get_leaves()  
                    user_data = session.get("user_data")
                    holidays = mongodb.get_fullholiday_data()
                    calendar_events = convert_to_fullcalendar(mongodb.get_all_events())
                    if all_user_leaves:               
                        all_formated_events = formated_leave(all_user_leaves)
                    else:
                        all_formated_events = []
                    all_calendar_events = calendar_events+all_formated_events+holidays
                    print("Entering into get mode")
                    name = user_data['name']
                    user_leaves = mongodb.get_leaves(name or [])
                    # print("user leaves:", user_leaves)
                    if user_leaves:               
                        formated_events = formated_leave(user_leaves)
                    else:
                        formated_events = []
                    #print("Formatted leaves,",formated_events)
                    
                    events = convert_to_fullcalendar(mongodb.get_user_events(user_data['name']) or [])
                    #print("User events:",events)
                    session["calendar_events"] = calendar_events
                    session["events"] = events
                    all_events = events+formated_events+holidays
                    print("All events:", all_events)
                    aggregated_leaves = mongodb.my_approved_events(
                        name)
                    print(aggregated_leaves)
                    if not aggregated_leaves:
                        aggregated_leaves = {}
                    session["aggregated_leaves"] = aggregated_leaves
                    # print("Executing User console:")
                    # print("User Data:", user_data)
                    #print("User events:",events)
                    # print("Calendar_events:",calendar_events)
                    return render_template("user_console.html", user=user_data, events=all_events, calendar_events=all_calendar_events,aggregated_leaves=aggregated_leaves)
            
            flash("Please log in to access your console.", "warning")
            return redirect(url_for("home"))
        return redirect(url_for("home"))
    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error occurred in user_console: {str(e)}")
        flash("An unexpected error occurred. Please try again later.", "danger")
        return redirect(url_for("home"))


        
@app.route('/signup', methods=["GET", "POST"])
def signup():
    teams = mongodb.get_teams() if isinstance(mongodb.get_managers(), list) else []
    if type(teams) == list:
        return render_template("signup.html", teams=teams)
    else:
        teams = []
        return render_template("signup.html", teams=teams)

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        email = request.form.get("email")
        team = request.form.get("team")
        password = request.form.get("password")
        result = mongodb.signup(email, password, team)
        print("Result from mongodb", result)
        data = {"email":email, "team":team,"password":password}
        if result:
            flash("User ID has been successfully created!","success")
            app_logger.debug(f"User ID has been successfully created for the user {email}:{team}")
            return redirect(url_for("home"))
        else:
            flash("Failed to create the ID!", "error")
            app_logger.debug(f"User ID has been successfully created for the user {email}:{team}")
            return redirect(url_for("signup"))

@app.route("/admin_console", methods=["GET", "POST"])
def admin_console():
    managers = mongodb.get_managers() if isinstance(mongodb.get_managers(), list) else []
    teams = mongodb.get_teams() if isinstance(mongodb.get_managers(), list) else []
    admins = mongodb.get_privilege() if isinstance(mongodb.get_managers(), list) else []
    print(admins)
    return render_template("management_console.html", managers=managers, teams=teams, admins=admins)

@app.route("/add_access", methods=["GET", "POST"])
def add_access():
    if request.method == "POST":
        email = request.form.get("email")
        access = request.form.get("access")
        managers = mongodb.get_managers() if isinstance(mongodb.get_managers(), list) else []
        teams = mongodb.get_teams() if isinstance(mongodb.get_managers(), list) else []
        admins = mongodb.get_privilege() if isinstance(mongodb.get_managers(), list) else []
        print(email, access)
        if email and access:
            response = mongodb.add_access(email,access)
            if response:
                flash(f"Access modified for the user {email} with {access}", "success")
                app_logger.debug(f"Access modified for the user {email} with {access}")
                return redirect(url_for('user_console'))
            else:
                flash(f"Failed to modify the privilege for the user {email} with {access}", "error")
                app_logger.debug(f"Failed to modify the privilege for the user {email} with {access}")
                return redirect(url_for('user_console'))

@app.route("/add_team", methods=["GET", "POST"])
def add_team():
    if request.method == "POST":
        team = request.form.get("team")
        manager = request.form.get("manager")
        if team and manager:
            response = mongodb.add_team(team,manager)
            if response:
                flash(f"Added {team} under {manager}", "success")
                app_logger.debug(f"Added {team} under {manager}")
                return redirect(url_for('user_console'))
            else:
                flash(f"Failed to add {team} under {manager}", "error")
                app_logger.debug(f"Failed to add {team} under {manager}")
                return redirect(url_for('user_console'))

@app.route("/add_new_member", methods = ["GET", "POST"])
def add_new_member():
    if request.method == "POST":
        name = request.form.get("name")
        user_email = request.form.get("user_email")
        empid = request.form.get("empid")
        team = request.form.get("team","")
        position = request.form.get("position")
        data = {"name":name, "email":user_email, "empid":empid, "team":team,"position":position}
        response = mongodb.add_new_user(data)
        if response:
            flash(f"Added {user_email} to the team {team}", "success")
            app_logger.debug(f"Added {user_email} to the team {team}")
            return redirect(url_for('user_console'))
        else:
            app_logger.debug(f"Failed to add {user_email} due to {response}")
            flash(f"Failed to add {user_email} due to {response}","error")
            return redirect(url_for('user_console'))
        

@app.route("/apply_event", methods=["POST", "GET"])
def apply_event():
    if "user_data" not in session:
        flash("Please log in to access your schedule.", "warning")
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email")
        date = request.form.get("date")
        event = request.form.get("event")
        name = request.form.get("name")
        user_data = session["user_data"]
        team = user_data["team"]
        color = "purple"
        status = "pending"
        comment = request.form.get("comment")
        data = {"email":email, "name":name,"date":date, "event":event}
        response = mongodb.insert_event(date,event,name,
                                        team,color,
                                        status,comment)
        if response:
            app_logger.debug(f"{event} applied on {date} successfully for the user {email}")
            flash(f"{event} applied on {date} successfully", "success")
            return redirect(url_for('user_console'))
        else:
            app_logger.debug(f"Unable to apply {event} on {date} for the user {email}")
            flash(f"Unable to apply {event} on {date}", "error")
            return redirect(url_for('user_console'))
        
@app.route("/add_schedule", methods={"POST","GET"})
def add_schedule():
    
    if request.method == "POST":
        # Parse start and end dates
        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")
        selected_users = request.form.getlist("selected_users")
        # Convert start and end dates to datetime objects
        start_date_obj = datetime.strptime(startdate, "%Y-%m-%d")
        end_date_obj = datetime.strptime(enddate, "%Y-%m-%d")
        # shift = request.form.get

        # Extract the year and month from the start_date
        schedule_for = str(f"{start_date_obj.year}-{start_date_obj.month}")
        print(schedule_for)
        users_with_teams = serialize_mongo_data(mongodb.users())
        data_list = []
        # Generate schedule for each user
        for user in selected_users:
            current_date = start_date_obj
            schedule_dict = {}
            date_shift_dict = {}
            user_team = next((user_data['team'] for user_data in users_with_teams if user_data['name'] == user), None)
            date_shift_dict["name"] = user
            print("Creating schedule for the user:", user)
            date_shift_dict["team"] = user_team
            shift_key = f"schedule_{user}"
            shift = request.form.get(shift_key, "N")
            weekoff_key = f"weekoff_{user}"
            weekoff_dates_raw = request.form.get(weekoff_key, "")
            week_off_list = [date.strip() for date in weekoff_dates_raw.split(",")]
            print("Week off list for the user: ", week_off_list, user)
            while current_date <= end_date_obj:
                str_current_date = current_date.strftime("%Y-%m-%d")
                if str_current_date in week_off_list:
                    print("week off in schedule:", str_current_date)
                    schedule_dict[str_current_date] = "Week Off"
                else:
                    schedule_dict[str_current_date] = shift
                
                current_date += timedelta(days=1)  # Move to the next day
            date_shift_dict["schedule"] = schedule_dict
            print("date_shift_dict:", date_shift_dict)
            data_list.append(date_shift_dict)
        response = mongodb.add_schedule(data_list)
        email = session.get("user_data", {}).get("email")  # or however you stored it
        # password = session["password"]
        response = mongodb.add_schedule(data_list)
        # user_data = session["user_data"]
        # team_list = session["team_list"]
        users_with_teams = serialize_mongo_data(mongodb.users())
        if response:
            print("Response from mongodb is true, redirecting to user console with session data")
            # print(session["user_data"])
            # print(email)
            app_logger.debug("Schedule added successfully")
            flash("Schedule added successfully!", "success")
            return redirect(url_for('user_console'))  # Redirect to user console with session data intact
        else:
            print("Executing to login page")
            app_logger.debug("Error adding Schedule hence going back to user_console")
            flash("Error adding schedule!", "danger")
            return redirect(url_for('user_console'))
    else:
        return redirect(url_for('user_console'))


@app.route("/approve", methods=["GET", "POST"])
def approvals():
    if request.method == 'POST':
        # Get the list of pending requests stored in the session
        event_requests = session.get("pending_requests", [])
        updated_data = []

        total_rows = int(request.form[
                             'total_rows'])  # Get the total number of rows
        for i in range(1, total_rows + 1):
            user = request.form[
                f'user_{i}']  # Get the user for each row
            date = request.form[
                f'date_{i}']  # Get the date for each row
            status = request.form[
                f'status_{i}']  # Get the selected status for each row

            # Update the status in the event requests
            for request_entry in event_requests:
                if request_entry['user'] == user and \
                        request_entry['date'] == date:
                    request_entry[
                        'status'] = status  # Update the status field
                    updated_data.append(
                        request_entry)  # Keep the updated data

        # If any updates were made, call the function to update MongoDB
        if updated_data:
            print("Data to be updated:", updated_data)
            update_response = mongodb.update_requests(
                updated_data)
            if update_response:
                # Remove modified entries from the pending requests to avoid resubmission
                session["pending_requests"] = [r for r in
                                               event_requests
                                               if
                                               r not in updated_data]
                app_logger.debug("Requests Approved / Denied successfully!")
                flash(
                    "Requests Approved / Denied successfully!",
                    "success")
            else:
                app_logger.debug("Failed to update the request due to an error")
                flash(
                    "Failed to update the request due to an error",
                    "error")
        else:
            app_logger.debug("No updates were made!")
            flash("No updates were made.", "info")

        return redirect(url_for(
            'user_console'))  # Redirect to user console

@app.route("/logout", methods=["GET", "POST"])
def logout():
    # Clear the session data (or any other logout logic you might need)
    session.clear()  # This will remove all session data (including user info)

    # Redirect the user to the home page after logging out
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
