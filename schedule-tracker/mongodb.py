import os
import pymongo
from pymongo.errors import ServerSelectionTimeoutError, \
    InvalidURI
import encryptor_decryptor
import logging
import csv
from logging.handlers import TimedRotatingFileHandler
from collections import Counter

# Create two separate loggers: one for general application logs, one for error logs
app_logger = logging.getLogger('app')

# Set the logging level
app_logger.setLevel(
    logging.DEBUG)  # For application logs, capture DEBUG and above

# Create TimedRotatingFileHandler for rotating logs every day
app_file_handler = TimedRotatingFileHandler('logs/app.log',
                                            when='midnight',
                                            interval=1,
                                            backupCount=7)  # Keep 7 days of logs

# Create log formats for the two loggers
app_format = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')

# Set the format for each handler
app_file_handler.setFormatter(app_format)

# Add handlers to the loggers
app_logger.addHandler(app_file_handler)
# Now you can use these loggers in your code


try:
    # Retrieve environment variables
    MONGO_HOST = os.getenv('MONGO_HOST', '')
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_USERNAME = os.getenv('MONGO_USERNAME', '')
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', '')
    MONGO_DB = os.getenv('MONGO_DB', 'mongoDb')

    # Construct the MongoDB URI

    # Attempt to connect to MongoDB
    url = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
    client = pymongo.MongoClient(url,
                                 serverSelectionTimeoutMS=5000)
    print(f"Attempting to connect to {url}")
    app_logger.debug(f"Attempting to connect to {url}")

    # Test the connection
    client.admin.command('ping')
    print("Connection successful")

except (ServerSelectionTimeoutError, InvalidURI) as e:
    # Handle the specific exception for server selection timeout
    print(f"Failed to connect to MongoDB server {url}: {e}")
    app_logger.debug(
        f"Failed to connect to MongoDB server {url}: "
        f"{e}")

    # Fallback to default localhost connection
    fallback_url = "mongodb://localhost:27017/mongoDb"
    try:
        client = pymongo.MongoClient(fallback_url,
                                     serverSelectionTimeoutMS=5000)
        print(
            f"Attempting to connect to fallback MongoDB server {fallback_url}")
        app_logger.debug(
            f"Attempting to connect to fallback MongoDB server {fallback_url}")

        # Test the fallback connection
        client.admin.command('ping')
        print("Fallback connection successful")
        app_logger.debug(f"Fallback connection successful")

    except ServerSelectionTimeoutError as fallback_e:
        # Handle fallback connection error
        print(
            f"Failed to connect to fallback MongoDB server {fallback_url}: {fallback_e}")
        app_logger.debug(
            f"Failed to connect to fallback MongoDB server {fallback_url}: {fallback_e}")

db = client["mongoDb"]
role_db = db["role_test"]
user_db = db["users_test"]
team_db = db["teams_test"]
events_collection = db['events_test']
leaves = db["leaves_test"]
holiday_collection = db['holiday_test']


def format_date(date_str):
    try:
        # Convert the string date to datetime object
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"Date format error for {date_str}: {e}")
        return None


def update_holiday_entry(date, event, comment, option):
    try:
        # Format the date to the string used in MongoDB (date format)
        formatted_date = format_date(date)

        if formatted_date is None:
            return

        # Prepare the update document
        update = {
            "date": formatted_date,
            "event": event,
            "comment": comment,
            "option": option
        }

        # Check if the document exists
        existing_entry = holiday_collection.find_one(
            {"date": formatted_date})

        if existing_entry:
            # Update the document if exists
            result = holiday_collection.update_one(
                {"date": formatted_date},
                {"$set": update}
            )
            if result.matched_count > 0:
                # print(f"Updated holiday: {event} on {date}")
                app_logger.debug(
                    f"Updated holiday: {event} on {date}")
            else:
                app_logger.debug(
                    f"No update made for {event} on {date}")
                print(
                    f"No update made for {event} on {date}")
        else:
            # Insert a new document if not exists
            holiday_collection.insert_one(update)
            app_logger.debug(
                f"Inserted holiday: {event} on {date}")
            # print(f"Inserted holiday: {event} on {date}")

    except Exception as e:
        app_logger.debug(
            f"Error updating holiday for {date}: {e}")
        print(f"Error updating holiday for {date}: {e}")


def read_and_update_from_csv():
    try:
        with open('data/leave-calander.csv',
                  mode='r') as file:
            reader = csv.DictReader(
                file)  # Reads the CSV file into a dictionary format

            for row in reader:
                # Extract data from each row
                date = row['date']
                event = row['event']
                comment = row['comment']
                option = row['option']

                # Call the function to update MongoDB with data from the CSV
                update_holiday_entry(date, event, comment,
                                     option)
                app_logger.debug(
                    "Calling update_holiday_entry to seed the holidays as the app starts")

    except Exception as e:
        app_logger.debug(f"Error reading the CSV file: {e}")
        print(f"Error reading the CSV file: {e}")


def users():
    try:
        # Fetch users with the specified conditions
        users = list(user_db.find({
            "team": {"$ne": ""},
            # Ensure team is not null or empty
            "position": {
                "$nin": ["Manager", "Admin", "Director"]}
            # Exclude Manager, Admin, Director
        },
            {
                "email": 1, "team": 1, "role": 1, "name": 1,
                "_id": 0
                # Only include the name, team, and role fields in the result
            }))
        print(users)
        return users
    except Exception as e:
        return e


def add_new_user(data):
    try:
        email = data["email"]
        team = data["team"]

        old_data = user_db.find_one({"email": email})
        if not old_data:
            print(
                f"{email} was not already tagged to the {team}.  Tagged successfully!!")
            user_db.insert_one(data)
        else:
            print(
                f"{email} was already tagged to the {team}.  Not Tagged Now!!")
            pass
        return True
    except Exception as e:
        return e


def get_managers():
    try:
        managers = []
        result = user_db.find({})
        for value in result:
            position = value["position"]
            if position == "Manager":
                email = value["email"]
                managers.append(email)
        return managers
    except Exception as e:
        return e


def get_teams():
    try:
        teams = team_db.find({}, {
            "team": 1})  # Get only the "team" field
        team_list = list({team["team"] for team in
                          teams})  # Use a set to remove duplicates
        team_list.sort()
        return team_list
    except Exception as e:
        return e


def add_access(email, access):
    try:
        result = user_db.update_one(
            {"email": email},
            # filter to find the specific document
            {"$set": {"privilege": access}}
            # add or update the field
        )
        status = True
        print(result)
    except Exception as e:
        status = e
    return status


def add_team(team, manager):
    try:
        team_db.insert_one(
            {"team": team, "manager": manager})
        status = True
    except Exception as e:
        status = e
    return status


def get_privilege():
    try:
        admins = []

        result = user_db.find({})
        for doc in result:
            admins_dict = {}
            if "privilege" in doc:
                privilege = doc["privilege"]
                if privilege == "admin":
                    admins_dict["Name"] = doc["name"]
                    admins_dict["Email"] = doc["email"]
                    admins_dict["Position"] = doc[
                        "position"]
                    admins.append(admins_dict)

    except Exception as e:
        admins = []
    return admins


def signup(email, password, team):
    try:
        # Check if the user already exists using find_one() to get the first matching document
        user = user_db.find_one({"email": email})

        if user:
            print(user)
            # If the user exists, check if the team field is None
            if not user["team"]:
                print(
                    f"No Team had been tagged to the user.  Tagging {team} to {user["name"]}")
                # Encrypt password and get key
                decrypted_pass = encryptor_decryptor.encryptor(
                    password)
                dec_password = decrypted_pass[0]
                key = decrypted_pass[1]

                # Update the user's password, key, and team
                update_value = {
                    '$set': {"password": dec_password,
                             "key": key, "team": team,
                             "privilege": "engineer"}
                }
                update = user_db.update_one(
                    {"email": email}, update_value)

                # Check if the document was updated
                if update.modified_count > 0:
                    status = True
                    print(
                        "User updated successfully with team.")
                else:
                    status = "No changes were made to the user."
                    status = True
            else:
                print(
                    f"{user["name"]} has already been tagged to {user["team"]}")
                # If the team is not None, just update password and key
                decrypted_pass = encryptor_decryptor.encryptor(
                    password)
                dec_password = decrypted_pass[0]
                key = decrypted_pass[1]

                # Update only the password and key
                update_value = {
                    '$set': {"password": dec_password,
                             "key": key, "team": team,
                             "privilege": "engineer"}}
                update = user_db.update_one(
                    {"email": email}, update_value)

                # Check if the document was updated
                if update.modified_count > 0:
                    status = True
                    print(
                        "Password and key updated successfully.")
                else:
                    status = False
                    print(
                        "No changes were made to the user.")
        else:
            # If the user doesn't exist, return a message
            status = False
            print("User not found!")

    except Exception as e:
        # Return error message if an exception occurs
        status = f"Error: {str(e)}"

    return status


def login(email, password):
    try:
        user = user_db.find_one({"email": email})

        if user:
            db_pass = user["password"]
            db_key = user["key"]
            data = [db_pass, db_key]
            decrypted = encryptor_decryptor.decrypt(data)
            if decrypted == password:
                status = True
                user_data = {
                    "name": user["name"],
                    "email": user["email"],
                    "empid": user["empid"],
                    "position": user["position"],
                    "privilege": user["privilege"],
                    "team": user["team"]
                }
                print("User obtained from mongo login:",
                      user_data)
                return status, user_data
            else:
                print("Password Mismatch")
                return False, None

        else:
            return "No account found!!", None  # User not found
    except Exception as e:
        return f"Error: {str(e)}", None  # Return error if something goes wrong


def insert_event(date, event, name, team, color, status,
                 comment):
    try:
        existing_leaves = leaves.find(
            {"name": name, "team": team})
        date = datetime.strptime(date, "%Y-%m-%d")
        result = leaves.update_one(
            {"name": name, "team": team, },
            # Filter by name and team
            {"$set": {str(date): {"event": event,
                                  "status": status,
                                  "color": color,
                                  "comment": comment}}},
            # Set
            # the event for the specific date
            upsert=True
            # This ensures that if the document does not exist, it will be created
        )
        if result.modified_count > 0:
            print("Event updated successfully.")
            status = True
        elif result.upserted_id:
            print("Document inserted successfully.")
            status = True
        else:
            print("No changes were made.")
            status = True
    except Exception as e:
        print(f"Error inserting event: {str(e)}")
        status = False  # Indicate failure
    return status


def get_events(name):
    try:
        # Query to find events by email
        events = events_collection.find({
                                            "name": name})  # Sorting by date in ascending order
        event_list = []
        for event in events:
            if None in event.values():
                pass
            event_list.append(event)
        # print("Event list from mongo:", event_list)
        return event_list  # Return the list of events

    except Exception as e:
        print(f"Error fetching events: {str(e)}")
        return None  # Return None if there is an error


def get_user_by_email(email):
    try:
        user = user_db.find_one({"email": email})

        if user:
            # Ensure all fields are serializable
            for key, value in user.items():
                if value is None:
                    user[
                        key] = ""  # Replace None with empty string or a suitable default
            return user
        else:
            return None  # Return None if no user with that email is found

    except PyMongoError as e:
        print(f"Error fetching user by email: {str(e)}")
        return None  # Return None in case of an error


from datetime import datetime
from pymongo.errors import PyMongoError


# Assuming `events_collection` is already defined and connected to MongoDB

def apply_event(data):
    print("Applying event")
    try:
        # Parse the date from the input data
        date_to_remove = datetime.strptime(data["date"],
                                           "%Y-%m-%d")
        event = data["event"]
        # Prepare the query to check for the date in the schedule array
        query = {"email": data["email"],
                 f"schedule_for.{data['event_for']}.schedule": {
                     "$in": [date_to_remove]}
                 }

        # Prepare the update operation to remove the date from schedule and add to event
        update = {
            "$pull": {
                f"schedule_for.{data['event_for']}.schedule": date_to_remove},
            # Remove date from schedule (if it exists)
            "$push": {
                f"schedule_for.{data['event_for']}.event": date_to_remove}
            # Add date to event
        }

        # Perform the update operation
        result = events_collection.update_one(query, update)

        # If no documents are affected, the date wasn't in the schedule but we still push it to events
        if result.modified_count > 0:
            print("Date successfully moved to event.")
            status = True
        else:
            # If no document was modified, we still insert the date into the event array
            # Use a query to find the document and ensure the event array gets the date added
            print(
                "No matching document or date found in schedule. Adding date to events.")
            query = {
                f"schedule_for.{data['event_for']}.event": {
                    "$ne": date_to_remove}
                # Only add if not already present
            }
            print("Query to find the data", query)
            update = {
                "$push": {
                    f"schedule_for.{data['event_for']}.event": date_to_remove}
            }
            print("Query to update the data:", update)
            result = events_collection.update_one(query,
                                                  update)
            if result.modified_count > 0:
                print("Date added to event.")
                status = True
            else:
                print(
                    "An error occurred while adding the date to events.")
                status = False

    except PyMongoError as e:  # Catch any errors related to MongoDB operations
        print(
            f"An error occurred with the MongoDB operation: {e}")
        status = False
    except Exception as e:
        # Catch any other errors
        print(f"An unexpected error occurred: {e}")
        status = False

    return status


def add_schedule(data_list):
    statuses = []  # To store the status of each operation (True/False for each user)

    try:
        for data in data_list:
            user = data["name"]
            team = data["team"]
            new_schedule = data["schedule"]

            # Create a query to find the user and their team in the collection
            query = {"name": user, "team": team}

            # Find the user's current document
            user_doc = events_collection.find_one(query)

            if user_doc:
                # If the user exists, merge schedules
                current_schedule = user_doc.get("schedule",
                                                {})
                updated_schedule = current_schedule.copy()  # Start with the existing schedule

                # Overwrite or append each new date from the input schedule
                for date, shift in new_schedule.items():
                    updated_schedule[date] = shift

                # Update the document with the merged schedule
                update = {
                    "$set": {"schedule": updated_schedule}}
                events_collection.update_one(query, update)
                print(f"Schedule updated for user: {user}")
                statuses.append(True)
            else:
                # If the user does not exist, create a new document
                new_doc = {
                    "name": user,
                    "team": team,
                    "schedule": new_schedule
                }
                events_collection.insert_one(new_doc)
                print(
                    f"New document created for user: {user}")
                statuses.append(True)
    except PyMongoError as e:
        print(f"MongoDB error occurred: {e}")
        statuses.append(False)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        statuses.append(False)

    return statuses


def get_all_events():
    try:
        find = events_collection.find({}, {"_id": 0})
        data = []
        for items in find:
            data.append(items)
        return data
    except Exception as e:
        print(
            f"Error occurred while fetching data from MongoDB: {e}")
        return []


def get_user_events(name):
    try:
        find = events_collection.find({"name": name},
                                      {"_id": 0})
        data = []
        for items in find:
            data.append(items)
        return data
    except Exception as e:
        print(
            f"Error occurred while fetching data from MongoDB: {e}")
        return []


def get_leaves(name=None):
    try:
        # If no name is provided, find all users in the 'leaves' collection
        if name:
            user_leaves = leaves.find_one({"name": name},
                                          {"_id": 0})
            if user_leaves:
                fullcalendar_events = []
                # Extract leave events for a single user
                for date_str, event_info in user_leaves.items():
                    if date_str not in ["name", "team"]:
                        event_date = datetime.strptime(
                            date_str, "%Y-%m-%d %H:%M:%S")
                        event = {
                            "name": user_leaves["name"],
                            "team": user_leaves["team"],
                            "title": event_info["event"],
                            # Event name (e.g., "Leave")
                            "start": event_date.strftime(
                                "%Y-%m-%d"),
                            # Only the date part (YYYY-MM-DD)
                            "color": event_info["color"],
                            # Event color (e.g., "purple")
                            "status": event_info[
                                "status"],
                            # Event status (e.g., "pending")
                            "comment": event_info["comment"]
                        }
                        fullcalendar_events.append(event)
                return fullcalendar_events
            else:
                return []  # If no data for the specific user, return empty list
        else:
            user_leaves = leaves.find({}, {"_id": 0})
            fullcalendar_events = []
            # Iterate through the cursor and extract leave events for each user
            for user in user_leaves:
                for date_str, event_info in user.items():
                    if date_str not in ["name", "team"]:
                        event_date = datetime.strptime(
                            date_str, "%Y-%m-%d %H:%M:%S")
                        event = {
                            "name": user["name"],
                            "team": user["team"],
                            "title": event_info["event"],
                            # Event name (e.g., "Leave")
                            "start": event_date.strftime(
                                "%Y-%m-%d"),
                            # Only the date part (YYYY-MM-DD)
                            "color": event_info["color"],
                            # Event color (e.g., "purple")
                            "status": event_info[
                                "status"],
                            # Event status (e.g., "pending")
                            "comment": event_info["comment"]
                        }
                        fullcalendar_events.append(event)

            return fullcalendar_events

    except PyMongoError as e:
        print(f"MongoDB error occurred: {e}")
        return []  # Return an empty list if MongoDB error occurs

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []  # Return an empty list if other error occurs


def get_pending_leaves():
    try:
        # Query the collection
        documents = leaves.find({})  # Fetch all documents

        result = []

        for doc in documents:
            user = doc.get("name")
            team = doc.get("team")
            for key, value in doc.items():
                # Check if the key is a date and if the status is pending
                if isinstance(key,
                              str) and " " in key:  # Assuming date keys have a space separator
                    event_details = value
                    if isinstance(event_details,
                                  dict) and event_details.get(
                        "status") == "pending":
                        result.append({
                            "user": user,
                            "team": team,
                            "event": event_details.get(
                                "event"),
                            "date": key,
                            "need": event_details.get(
                                "comment",
                                None)
                            # Optional: add comment if available
                        })
        # print("Pending leaves from mongo:", result)
        return result
    except PyMongoError as e:
        print(f"MongoDB error occurred: {e}")
        return []  # Return an empty list if MongoDB error occurs

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []  # Return an empty list if other error occurs


def update_requests(data):
    try:
        # Convert the string date to datetime for proper querying in MongoDB
        def convert_to_datetime(date_str):
            return datetime.strptime(date_str,
                                     "%Y-%m-%d %H:%M:%S")

        # Update the documents in MongoDB
        for entry in data:
            # Convert the date to datetime object
            date = convert_to_datetime(entry["date"])
            print("Date to be updated:", date)

            # Format the date back to string format (for query matching)
            formatted_date = date.strftime(
                "%Y-%m-%d %H:%M:%S")  # Ensure this matches how it's stored in MongoDB

            # Update query to match the specific user, team, and date (formatted as a string)
            query = {
                "team": entry["team"],
                "name": entry["user"],
                f"{formatted_date}": {"$exists": True}
                # Matching with the exact date string
            }
            print("Query:", query)

            # If the status is "denied", remove the specific date field from the document
            if entry["status"] == "denied":
                # The update to remove the specific field with "denied" status
                update = {
                    "$unset": {
                        f"{formatted_date}": ""
                        # Remove the field with the denied status
                    }
                }
                result = leaves.update_one(query, update)
                if result.modified_count > 0:
                    print(
                        f"Successfully removed the denied request for {entry['user']} on {entry['date']}")
                else:
                    print(
                        f"No matching field found to remove for {entry['user']} on {entry['date']}")
            else:
                # The update to be applied if not "denied": change only the status
                update = {
                    "$set": {
                        f"{formatted_date}.status": entry[
                            "status"],
                        # Only update the status for that date
                    }
                }
                # Perform the update
                result = leaves.update_one(query, update)

                # Check if the update was successful
                if result.matched_count > 0:
                    print(
                        f"Successfully updated the status for {entry['user']} on {entry['date']}")
                else:
                    print(
                        f"No matching document found for {entry['user']} on {entry['date']}")

        return True  # Return True after all the updates are done

    except PyMongoError as e:
        print(f"MongoDB error occurred: {e}")
        return e  # Return error if MongoDB error occurs

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return e  # Return error if other unexpected error occurs


def get_fullholiday_data():
    try:
        holiday_list = []
        holidays = holiday_collection.find({}, {
            "_id": 0})  # Fetch all holidays excluding _id

        # Loop to add each holiday to the list
        for event in holidays:
            holiday_list.append(event)

        # Mapping 'option' to color
        option_colors = {
            'MANDATORY': '#90a4ae',
            'OPTIONAL': '#795548',
            'NATIONAL': '#ffccbc',
            'FESTIVAL': '#9e9d24'
            # Adjust these colors as needed
        }

        fullcalendar_events = []

        # Convert the holidays to FullCalendar format
        for holiday in holiday_list:
            event = {
                'title': holiday['event'] + ":" + holiday[
                    "comment"],
                "allDay": True,
                # Event name as the title
                'start': holiday['date'].isoformat(),
                # Start time (ISO format)
                'end': holiday['date'].replace(hour=23,
                                               minute=59,
                                               second=59).isoformat(),
                # Optional: End time
                'description': holiday['comment'],
                # Optional description
                'color': option_colors.get(
                    holiday['option'], 'gray')
                # Map 'option' to color, default to gray
            }
            fullcalendar_events.append(event)
        print(fullcalendar_events)
        return fullcalendar_events  # Return the list of events in FullCalendar format

    except PyMongoError as e:
        print(f"MongoDB error occurred: {e}")
        return None  # Return None in case of a MongoDB error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None  # Return None in case of an unexpected error


def my_approved_events(name):
    """
    Fetch and aggregate approved events for a given user.

    Args:
        name (str): The name of the user.

    Returns:
        list: A list of dictionaries containing aggregated event data with keys 'Option', 'Month', and 'Count'.
    """
    try:
        query = {"name": name}
        user_data = leaves.find_one(query)

        if not user_data:
            return []
        monthly_counts = Counter()
        for date, details in user_data.items():
            if isinstance(details,
                          dict) and 'event' in details and details.get(
                    "status") == "approved":
                event_date = datetime.strptime(date,
                                               "%Y-%m-%d %H:%M:%S")
                month = event_date.strftime("%B %Y")
                monthly_counts[
                    (details['event'], month)] += 1

        aggregated_events = [
            {"Option": option, "Month": month,
             "Count": count}
            for (option, month), count in
            monthly_counts.items()
        ]

        return aggregated_events
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


def summary():
    events_data = events_collection.find({}, {"_id": 0})
    leaves_data = leaves.find({}, {"_id": 0})
    consolidated_data = {}
    # Process events data
    for event in events_data:
        print(event)
        user_name = event['name']
        # print(event['team'])
        # print(user_name)
        if user_name not in consolidated_data:
            consolidated_data[user_name] = {
                'team': event['team'],
                'schedule': event['schedule'],
                'events': {},
                'leaves': {}
            }
        for date, details in event['schedule'].items():
            consolidated_data[user_name]['schedule'][
                date] = details

    # Process leaves data
    for leave in leaves_data:
        user_name = leave['name']
        if user_name not in consolidated_data:
            consolidated_data[user_name] = {
                'team': leave['team'],
                'schedule': {},
                'events': {},
                'leaves': {}
            }

        for date, details in leave.items():
            if date not in ['name', 'team']:
                consolidated_data[user_name]['leaves'][
                    date] = {
                    'event': details['event'],
                    'status': details['status'],
                    'color': details['color'],
                    'comment': details['comment']
                }

    return consolidated_data


data = summary()
print(data)
