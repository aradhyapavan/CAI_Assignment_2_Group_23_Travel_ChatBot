import streamlit as st
import pandas as pd
import login_signup
import re
import dateparser
from datetime import datetime, timedelta

from utils import (
    preprocess,
    extract_entities_with_bert,
    extract_dates,
    word_count,
    load_model,
    create_connection,
)

# Check if user is logged in and redirect to login if not
def check_login():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Please log in to access this page.")
        auth_option = st.sidebar.selectbox("Login or Signup", ["Login", "Signup"])
        if auth_option == "Login":
            login_signup.login()
        elif auth_option == "Signup":
            login_signup.signup()
        st.stop()

check_login()

# Load model and vectorizer
vectorizer, service_classifier = load_model()

# Create a database connection
conn = create_connection()
cursor = conn.cursor()

# Create table for storing user queries if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT,
        intent TEXT,
        locations TEXT,
        dates TEXT
    )
""")
conn.commit()

# Function to store user query in the database
def store_user_query(query, intent, locations, dates):
    cursor.execute("""
        INSERT INTO user_queries (user_query, intent, locations, dates)
        VALUES (?, ?, ?, ?)
    """, (query, intent, ', '.join(locations), ', '.join([date[1].strftime('%Y-%m-%d') for date in dates])))
    conn.commit()

st.title("Task 3: Database Query with Chatbot Interface")

# Provide example queries for Task 3
with st.chat_message("assistant"):
    st.markdown("""
    ### Examples for Enhanced Task 3:
    - "Show me available flights by Air India from Delhi to Mumbai in October."
    - "Are there any Deluxe Hotel rooms available in Jaipur ?"
    - "I need to rent a Car in Bangalore next Monday."
    """)

if 'conversation_history_task3' not in st.session_state:
    st.session_state.conversation_history_task3 = []

# Display previous chat history
for chat in st.session_state.conversation_history_task3:
    with st.chat_message(chat['role']):
        st.markdown(chat['message'])

# User query input
query_task_3 = st.chat_input("What's your travel-related query?")

# Function to map intents to services and categories
def map_intent_to_service(intent):
    service_categories = {
        "flight": ["flight_booking", "flight_inquiry", "flight_cancellation", "flight_status", "flight_change"],
        "hotel": ["hotel_booking", "hotel_inquiry", "hotel_cancellation", "hotel_upgrade", "hotel_amenities"],
        "car_rental": ["car_rental", "car_inquiry", "car_cancellation", "car_extension", "car_price"],
        "travel_advisory": ["travel_advisory", "weather_advisory", "health_advisory", "political_unrest_advisory", "covid_restrictions"]
    }

    intent_service_map = {
        "flight_booking": "Book a flight",
        "flight_inquiry": "Flight availability inquiry",
        "flight_cancellation": "Cancel a flight",
        "flight_status": "Check flight status",
        "flight_change": "Change flight details",
        "hotel_booking": "Book a hotel",
        "hotel_inquiry": "Hotel availability inquiry",
        "hotel_cancellation": "Cancel a hotel reservation",
        "hotel_upgrade": "Upgrade hotel room",
        "hotel_amenities": "Inquire about hotel amenities",
        "car_rental": "Rent a car",
        "car_inquiry": "Car availability inquiry",
        "car_cancellation": "Cancel car rental",
        "car_extension": "Extend car rental period",
        "car_price": "Check car rental prices",
        "travel_advisory": "Get travel advisory information",
        "weather_advisory": "Get weather advisory",
        "health_advisory": "Get health advisory",
        "political_unrest_advisory": "Get political unrest advisory",
        "covid_restrictions": "Get COVID-19 travel restrictions"
    }

    for category, intents in service_categories.items():
        if intent in intents:
            return intent_service_map[intent], category

    return "Unknown service", "unknown"

# Function to extract dates, including months like 'October' and relative expressions like 'next week'

# Function to extract dates, including months like 'October' and relative expressions like 'next week'
def extract_dates(query):
    parsed_dates = []
    query_lower = query.lower()

    # Regular expressions to capture months
    months = r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    month_matches = re.findall(months, query_lower)
    
    for match in month_matches:
        # Convert the extracted month into the first and last day of the month
        first_day = dateparser.parse(f"1 {match}", settings={'PREFER_DAY_OF_MONTH': 'first'})
        last_day = dateparser.parse(f"last day of {match}")
        if first_day and last_day:
            parsed_dates.append((match, first_day))
            parsed_dates.append((match, last_day))
    
    # Also extract any specific dates or relative terms like "next week"
    extracted_dates = dateparser.search.search_dates(query)
    if extracted_dates:
        for date in extracted_dates:
            # Handle relative terms like "next week" by calculating a range
            if "next week" in date[0]:
                today = dateparser.parse("today")
                next_monday = today + timedelta((7 - today.weekday()) % 7 + 1)  # next Monday
                next_sunday = next_monday + timedelta(days=6)
                parsed_dates.append(("next week", next_monday))
                parsed_dates.append(("next week", next_sunday))
            else:
                parsed_dates.append(date)

    return parsed_dates

# Like term search based on extracted entities
def get_like_term(entity_type, entities):
    """Get LIKE term for column-specific filtering (e.g., Airline, Car Type)"""
    for entity in entities:
        if entity['entity'] == entity_type:
            return f"%{entity['word']}%"
    return None

# Process user query
if query_task_3:
    if word_count(query_task_3) < 4:
        st.warning("Please enter a more detailed query (at least 4 words).")
    else:
        # Store user's query in chat history
        st.session_state.conversation_history_task3.append({"role": "user", "message": query_task_3})
        with st.chat_message("user"):
            st.markdown(query_task_3)

        # Preprocess the query and predict the service
        with st.spinner("Processing..."):
            processed_query = preprocess(query_task_3)
            query_tfidf = vectorizer.transform([processed_query])
            predicted_intent = service_classifier.predict(query_tfidf)[0]

            # Map the predicted intent to a service and category
            service, category = map_intent_to_service(predicted_intent)

            # Extract entities and dates
            entities, locations = extract_entities_with_bert(query_task_3)
            dates = extract_dates(query_task_3)

        # Store user query, intent, locations, and dates in the database
        store_user_query(query_task_3, predicted_intent, locations, dates)

        # Respond based on the predicted service
        bot_reply = f"You are asking about **{service}** (Category: {category})."

        if locations:
            bot_reply += f" You mentioned the following **locations**: {', '.join(locations)}."
        if dates:
            bot_reply += f" The **date(s)** mentioned: {', '.join([date[1].strftime('%Y-%m-%d') for date in dates])}."

        # Query the database based on predicted service and extracted entities
        result_data = None  # Placeholder for query result
        result_columns = []  # Placeholder for column headers

        if category == 'flight' and len(locations) >= 2:
            origin, destination = locations[0], locations[1]
            airline_like = get_like_term('I-ORG', entities)

            if dates:
                date = dates[0][1].strftime('%Y-%m')
                cursor.execute("""
                    SELECT * FROM flight 
                    WHERE LOWER(Source)=LOWER(?) AND LOWER(Destination)=LOWER(?) 
                      AND strftime('%Y-%m', Date_of_Journey)=? 
                      AND (LOWER(Airline) LIKE ? OR ? IS NULL)
                """, (origin, destination, date, airline_like, airline_like))
            else:
                cursor.execute("""
                    SELECT * FROM flight 
                    WHERE LOWER(Source)=LOWER(?) AND LOWER(Destination)=LOWER(?) 
                      AND (LOWER(Airline) LIKE ? OR ? IS NULL)
                """, (origin, destination, airline_like, airline_like))
            flights_data = cursor.fetchall()

            if flights_data:
                result_data = flights_data
                result_columns = ["Airline", "Source", "Destination", "Date_of_Journey", "Dep_Time", "Duration", "Total_Stops", "Price", "Additional_Info", "Arrival_Time"]
            else:
                bot_reply += " No flights found for the given criteria."

        elif category == 'hotel' and len(locations) >= 1:
                city = locations[0]
                room_type_like = get_like_term('I-ROOM', entities)  # Room type term

                if dates and len(dates) >= 2:
                    # Assuming dates[0] is the start date and dates[1] is the end date for 'next week'
                    start_date = dates[0][1].strftime('%Y-%m-%d')
                    end_date = dates[1][1].strftime('%Y-%m-%d')
                    
                    cursor.execute("""
                        SELECT * FROM hotel 
                        WHERE LOWER(City)=LOWER(?) 
                          AND Check_In_Date BETWEEN ? AND ?
                          AND (LOWER(Room_Type) LIKE ? OR ? IS NULL)
                    """, (city, start_date, end_date, room_type_like, room_type_like))
                else:
                    cursor.execute("""
                        SELECT * FROM hotel 
                        WHERE LOWER(City)=LOWER(?) 
                          AND (LOWER(Room_Type) LIKE ? OR ? IS NULL)
                    """, (city, room_type_like, room_type_like))
                
                hotels_data = cursor.fetchall()

                if hotels_data:
                    result_data = hotels_data
                    result_columns = ["Hotel_Name", "City", "Check_In_Date", "Room_Type", "Price_Per_Night", "Availability_Status", "Additional_Info", "Check_Out_Date", "Total_Nights"]
                else:
                    bot_reply += " No hotels found for the given criteria."



        elif category == 'car_rental' and len(locations) >= 1:
            city = locations[0]
            car_type_like = get_like_term('I-CAR', entities)  # Car type term

            if dates:
                date = dates[0][1].strftime('%Y-%m-%d')
                cursor.execute("""
                    SELECT * FROM car_rental 
                    WHERE LOWER(City)=LOWER(?) AND Pickup_Date=? 
                      AND (LOWER(Car_Type) LIKE ? OR ? IS NULL)
                """, (city, date, car_type_like, car_type_like))
            else:
                cursor.execute("""
                    SELECT * FROM car_rental 
                    WHERE LOWER(City)=LOWER(?) 
                      AND (LOWER(Car_Type) LIKE ? OR ? IS NULL)
                """, (city, car_type_like, car_type_like))
            car_rental_data = cursor.fetchall()

            if car_rental_data:
                result_data = car_rental_data
                result_columns = ["Car_Rental_Company", "City", "Pickup_Date", "Car_Type", "Price_Per_Day", "Availability_Status", "Additional_Info", "Return_Date", "Total_Days"]
            else:
                bot_reply += f" No car rentals found in {city}."

        elif category == 'travel_advisory' and len(locations) >= 1:
            city = locations[0]
            cursor.execute("""
                SELECT * FROM travel_advisory 
                WHERE LOWER(City)=LOWER(?)
            """, (city,))
            advisories_data = cursor.fetchall()

            if advisories_data:
                result_data = advisories_data
                result_columns = ["City", "Advisory_Date", "Advisory_Level", "Reason", "Affected_Routes", "Additional_Info", "Validity"]
            else:
                bot_reply += " No advisories found for the given location."

        else:
            bot_reply += " Sorry, I couldn't find enough information to answer your query."

        # Store bot reply in chat history
        st.session_state.conversation_history_task3.append({"role": "bot", "message": bot_reply})

        # Display bot reply
        with st.chat_message("assistant"):
            st.markdown(bot_reply)

        # Display the result data in a full-width container below the query options
        if result_data:
            st.write("### Results")
            with st.container():
                result_df = pd.DataFrame(result_data, columns=result_columns)
                st.dataframe(result_df, use_container_width=True)

# Cities list
cities = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Jaipur']

# ---- Additional Query Options in Horizontal Layout with Dynamic 'To Date' ----
st.write("### Additional Query Options")

# Horizontal layout for Query Flights
with st.container():
    st.write("#### Query Flights")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        origin_flight = st.selectbox("Origin city:", options=[city for city in cities if city != st.session_state.get("destination_flight")], key="origin_flight")
    with col2:
        destination_flight = st.selectbox("Destination city:", options=[city for city in cities if city != st.session_state.get("origin_flight")], key="destination_flight")
    with col3:
        from_date_flight = st.date_input("From Date (optional)", value=None, key="from_date_flight")
    if from_date_flight:
        with col4:
            to_date_flight = st.date_input("To Date (optional)", value=None, key="to_date_flight")
    
    col_button = st.columns([1])
    with col_button[0]:
        if st.button("Query Flights"):
            flights_data = None
            if origin_flight and destination_flight:
                query_flight = f"Show me available flights from {origin_flight} to {destination_flight}."
                intent = 'flight_inquiry'
                locations = [origin_flight, destination_flight]
                dates = [(None, from_date_flight)] if from_date_flight else []
                # Store flight query in the database
                store_user_query(query_flight, intent, locations, dates)

                if from_date_flight and to_date_flight:
                    cursor.execute("SELECT * FROM flight WHERE LOWER(Source)=LOWER(?) AND LOWER(Destination)=LOWER(?) AND Date_of_Journey BETWEEN ? AND ?", 
                                   (origin_flight, destination_flight, from_date_flight.strftime("%Y-%m-%d"), to_date_flight.strftime("%Y-%m-%d")))
                elif from_date_flight:
                    cursor.execute("SELECT * FROM flight WHERE LOWER(Source)=LOWER(?) AND LOWER(Destination)=LOWER(?) AND Date_of_Journey >= ?", 
                                   (origin_flight, destination_flight, from_date_flight.strftime("%Y-%m-%d")))
                else:
                    cursor.execute("SELECT * FROM flight WHERE LOWER(Source)=LOWER(?) AND LOWER(Destination)=LOWER(?)", 
                                   (origin_flight, destination_flight))
                flights_data = cursor.fetchall()
                if flights_data:
                    flight_df = pd.DataFrame(flights_data, columns=["Airline", "Source", "Destination", "Date_of_Journey", "Dep_Time", "Duration", "Total_Stops", "Price", "Additional_Info", "Arrival_Time"])
                    st.write("### Available Flights:")
                    st.dataframe(flight_df, use_container_width=True)
                else:
                    st.write("No flights available for the selected route.")

# Horizontal layout for Query Hotels
with st.container():
    st.write("#### Query Hotels")
    col6, col7, col8 = st.columns(3)
    with col6:
        location_hotel = st.selectbox("Hotel location:", options=cities, key="location_hotel")
    with col7:
        from_date_hotel = st.date_input("From Date (optional)", value=None, key="from_date_hotel")
    to_date_hotel = None  # Define to_date_hotel in all cases to avoid NameError
    if from_date_hotel:
        with col8:
            to_date_hotel = st.date_input("To Date (optional)", value=None, key="to_date_hotel")

    col_button = st.columns([1])
    with col_button[0]:
        if st.button("Query Hotels"):
            from_date_hotel_str = from_date_hotel.strftime("%Y-%m-%d") if from_date_hotel else None
            to_date_hotel_str = to_date_hotel.strftime("%Y-%m-%d") if to_date_hotel else None
            query_hotel = f"Show me available hotels in {location_hotel}."
            intent = 'hotel_inquiry'
            locations = [location_hotel]
            dates = [(None, from_date_hotel)] if from_date_hotel else []
            # Store hotel query in the database
            store_user_query(query_hotel, intent, locations, dates)

            hotels_data = None
            if from_date_hotel and to_date_hotel:
                # Query between the two dates
                cursor.execute("SELECT * FROM hotel WHERE LOWER(City)=LOWER(?) AND Check_In_Date<=? AND Check_Out_Date>=?", 
                               (location_hotel, to_date_hotel_str, from_date_hotel_str))
            elif from_date_hotel:
                # Query from a specific date onwards
                cursor.execute("SELECT * FROM hotel WHERE LOWER(City)=LOWER(?) AND Check_Out_Date>=?", (location_hotel, from_date_hotel_str))
            else:
                # Query without any date restrictions
                cursor.execute("SELECT * FROM hotel WHERE LOWER(City)=LOWER(?)", (location_hotel,))
            
            hotels_data = cursor.fetchall()
            if hotels_data:
                hotel_df = pd.DataFrame(hotels_data, columns=["Hotel_Name", "City", "Check_In_Date", "Room_Type", "Price_Per_Night", "Availability_Status", "Additional_Info", "Check_Out_Date", "Total_Nights"])
                st.write("### Available Hotels:")
                st.dataframe(hotel_df, use_container_width=True)
            else:
                st.write("No hotels available in the selected location and date range.")

# Horizontal layout for Query Car Rentals
with st.container():
    st.write("#### Query Car Rentals")
    col10, col11, col12 = st.columns(3)
    with col10:
        location_car = st.selectbox("Car rental location:", options=cities, key="location_car")
    with col11:
        from_date_car = st.date_input("From Date (optional)", value=None, key="from_date_car")
    if from_date_car:
        with col12:
            to_date_car = st.date_input("To Date (optional)", value=None, key="to_date_car")
    
    col_button = st.columns([1])
    with col_button[0]:
        if st.button("Query Car Rentals"):
            query_car = f"Show me available car rentals in {location_car}."
            intent = 'car_inquiry'
            locations = [location_car]
            dates = [(None, from_date_car)] if from_date_car else []
            # Store car rental query in the database
            store_user_query(query_car, intent, locations, dates)

            car_rental_data = None
            if location_car:
                if from_date_car and to_date_car:
                    cursor.execute("""
                        SELECT * FROM car_rental 
                        WHERE LOWER(City)=LOWER(?) 
                        AND Pickup_Date BETWEEN ? AND ?
                    """, (location_car, from_date_car.strftime("%Y-%m-%d"), to_date_car.strftime("%Y-%m-%d")))
                elif from_date_car:
                    cursor.execute("""
                        SELECT * FROM car_rental 
                        WHERE LOWER(City)=LOWER(?) 
                        AND Pickup_Date >= ?
                    """, (location_car, from_date_car.strftime("%Y-%m-%d")))
                else:
                    cursor.execute("SELECT * FROM car_rental WHERE LOWER(City)=LOWER(?)", (location_car,))
                
                car_rental_data = cursor.fetchall()
                if car_rental_data:
                    car_rental_df = pd.DataFrame(car_rental_data, columns=["Car_Rental_Company", "City", "Pickup_Date", "Car_Type", "Price_Per_Day", "Availability_Status", "Additional_Info", "Return_Date", "Total_Days"])
                    st.write("### Available Car Rentals:")
                    st.dataframe(car_rental_df, use_container_width=True)
                else:
                    st.write(f"No car rentals available in {location_car}.")

# Horizontal layout for Query Travel Advisories
with st.container():
    st.write("#### Query Travel Advisories")
    col14 = st.columns(1)
    with col14[0]:
        location_advisory = st.selectbox("Location for advisories:", options=cities, key="location_advisory")
    
    col_button = st.columns([1])
    with col_button[0]:
        if st.button("Query Travel Advisories"):
            query_advisory = f"Show me travel advisories for {location_advisory}."
            intent = 'travel_advisory'
            locations = [location_advisory]
            dates = []  # No specific dates for advisories
            # Store travel advisory query in the database
            store_user_query(query_advisory, intent, locations, dates)

            advisories_data = None
            if location_advisory:
                cursor.execute("SELECT * FROM travel_advisory WHERE LOWER(City)=LOWER(?)", (location_advisory,))
                advisories_data = cursor.fetchall()

                if advisories_data:
                    advisory_df = pd.DataFrame(advisories_data, columns=["City", "Advisory_Date", "Advisory_Level", "Reason", "Affected_Routes", "Additional_Info", "Validity"])
                    st.write("### Available Advisories:")
                    st.dataframe(advisory_df, use_container_width=True)
                else:
                    st.write(f"No advisories available in {location_advisory}.")

# Commit changes to the database
conn.commit()

# Close the connection at the end             
conn.close()

