import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import login_signup
from utils import get_flight_offers, get_hotel_list_by_city, get_car_rentals, get_vehicle_details_by_car_id

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

def reset_database():
    c.execute("DROP TABLE IF EXISTS api_data")
    c.execute("DROP TABLE IF EXISTS bookings")
    conn.commit()
    setup_db()

# Connect to SQLite database
conn = sqlite3.connect('travel_booking.db', check_same_thread=False)
c = conn.cursor()

# Create tables for API data caching and booking history
def setup_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_data (
            service_type TEXT,
            response_data TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT,
            user_email TEXT,  -- Add user_email to track bookings by user
            service_type TEXT,
            details TEXT,
            booking_date TEXT,
            canceled INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

setup_db()



# Greeting and Overview of Booking System
st.title("🤖 Welcome to Travel Services!")
if 'name' in st.session_state:  # Using 'name', not 'user_name'
    st.markdown(f"Hello, {st.session_state['name']}! I'm here to assist you with your travel needs.")
else:
    st.markdown("Hello! I'm here to assist you with your travel needs.")

st.markdown("""
### 🛠️ How It Works:
1. **Flight Booking**: Select your source and destination cities, choose departure and return dates, and pick your travel class. Confirm your booking.
2. **Hotel Booking**: Choose a city, search for available hotels, select your preferred hotel and room type. Confirm your booking.
3. **Car Rental**: Select a city and search for available rental cars, choose pick-up and drop-off dates, confirm your booking.
4. **Cancellation Policy**: Cancel bookings within **24 hours** of booking date if eligible.
""")

# Function to generate unique booking ID
def generate_booking_id(service_type):
    prefix = {'flight': 'FL', 'hotel': 'HL', 'car': 'CR'}
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix.get(service_type, 'XX')}{timestamp}"

# Cache API data
def cache_api_data(service_type, data):
    c.execute("DELETE FROM api_data WHERE service_type=?", (service_type,))
    c.execute("INSERT INTO api_data (service_type, response_data) VALUES (?, ?)", (service_type, str(data)))
    conn.commit()

# Fetch cached API data
def fetch_cached_api_data(service_type):
    c.execute("SELECT response_data FROM api_data WHERE service_type=?", (service_type,))
    row = c.fetchone()
    if row:
        return eval(row[0])  # Convert string back to dict
    return None

# Store booking details in DB with a unique booking ID and user email
def store_booking(service_type, details):
    if 'email' not in st.session_state:  # Using 'email', not 'user_email'
        st.error("User email is not available. Please log in.")
        return None

    booking_id = generate_booking_id(service_type)
    user_email = st.session_state['email']  # Fetch user email from session state
    c.execute("INSERT INTO bookings (booking_id, user_email, service_type, details, booking_date, canceled) VALUES (?, ?, ?, ?, ?, ?)",
              (booking_id, user_email, service_type, str(details), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0))
    conn.commit()
    return booking_id

# Fetch booking history for the logged-in user
def fetch_booking_history(user_email, canceled=0):
    try:
        c.execute("SELECT booking_id, service_type, details, booking_date FROM bookings WHERE user_email=? AND canceled=?", (user_email, canceled))
        return c.fetchall()
    except sqlite3.OperationalError as e:
        st.error(f"An error occurred with the database: {e}")
        return []

# Delete booking (Cancel)
def cancel_booking(booking_id, user_email):
    c.execute("UPDATE bookings SET canceled=1 WHERE booking_id=? AND user_email=?", (booking_id, user_email))
    conn.commit()

# Helper functions for handling API responses and pricing
def convert_to_inr(eur_price):
    conversion_rate = 110
    return float(eur_price) * conversion_rate

# Function to check if a booking is within 24 hours
def is_within_24_hours(booking_date_str):
    booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d %H:%M:%S')
    return (datetime.now() - booking_date).total_seconds() <= 24 * 3600

def calculate_hotel_price(room_type, num_days):
    room_prices = {"Single": 2000, "Double": 3500, "Suite": 6000, "Deluxe": 8000}
    return room_prices.get(room_type, 0) * num_days

def calculate_car_price(car_type, num_days):
    car_prices = {"Economy": 1500, "SUV": 3000, "Luxury": 5000, "Van": 4000}
    return car_prices.get(car_type, 0) * num_days

# Flight Booking Function
def flight_booking():
    st.header("Flight Booking")
    city_iata_mapping = {"Mumbai": "BOM", "Delhi": "DEL", "Bangalore": "BLR", "Hyderabad": "HYD", "Chennai": "MAA",
                         "Kolkata": "CCU", "Pune": "PNQ", "Jaipur": "JAI"}

    source_city = st.selectbox("Select Source City", list(city_iata_mapping.keys()), key="flight_source")
    destination_city = st.selectbox("Select Destination City", list(city_iata_mapping.keys()), key="flight_destination")

    if source_city == destination_city:
        st.error("Source and Destination cannot be the same.")
    else:
        departure_date = st.date_input("Departure Date", min_value=datetime.now().date(), key="flight_departure")

        # Automatically adjust the return date if it's earlier than the departure date
        if "flight_return" not in st.session_state:
            st.session_state.flight_return = departure_date
        elif st.session_state.flight_return < departure_date:
            st.session_state.flight_return = departure_date

        return_date = st.date_input("Return Date (optional)", 
                                    min_value=departure_date, 
                                    value=st.session_state.flight_return, 
                                    key="flight_return")

        travel_class = st.selectbox("Select Class", ["Business", "First"], key="flight_class")

        # Fetch flight data on search
        if st.button("Search Flights"):
            with st.spinner("Fetching flight data..."):
                flight_data = get_flight_offers(
                    city_iata_mapping[source_city],
                    city_iata_mapping[destination_city],
                    departure_date.strftime('%Y-%m-%d'),
                    return_date.strftime('%Y-%m-%d') if return_date else None
                )
                
                # Cache the flight data if available
                if flight_data:
                    cache_api_data('flight', flight_data)

        # After search or if cached data exists, show flight options
        flight_data = fetch_cached_api_data('flight')
        if flight_data:
            offers = flight_data.get("data", [])[:5]
            flight_options = []
            for offer in offers:
                base_price = float(offer["price"]["total"])
                inr_price = convert_to_inr(base_price)
                flight_options.append(f"Price: {inr_price:.2f} INR {travel_class}")

            selected_flight = st.selectbox("Select a Flight", flight_options, key="flight_selection")
            payment_method = st.radio("Select Payment Method", ["Credit Card", "Debit Card", "UPI"], key="flight_payment")

            if st.button("Confirm Booking", key="confirm_flight"):
                booking_details = {
                    "source": source_city,
                    "destination": destination_city,
                    "departure_date": str(departure_date),
                    "return_date": str(return_date),
                    "travel_class": travel_class,
                    "selected_flight": selected_flight,
                    "payment_method": payment_method,
                    "booking_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                booking_id = store_booking('flight', booking_details)
                st.success(f"Flight booked successfully! Booking ID: {booking_id}")

# Hotel Booking Function
def hotel_booking():
    st.header("Hotel Booking")
    
    # Maintain selected city in session state to avoid resetting
    if 'selected_city' not in st.session_state:
        st.session_state.selected_city = None
    city = st.selectbox("Select City", ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"], 
                        index=0 if st.session_state.selected_city is None else ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"].index(st.session_state.selected_city), 
                        key="hotel_city")
    
    if st.button("Search Hotels"):
        # Update session state with the selected city
        st.session_state.selected_city = city

        # Ensure hotel data persists in session state
        if 'hotel_data' not in st.session_state:
            with st.spinner("Fetching hotel data..."):
                st.session_state.hotel_data = get_hotel_list_by_city(city)

    if 'hotel_data' in st.session_state:
        hotel_options = [f"{hotel['name']} - ID: {hotel['hotelId']}" for hotel in st.session_state.hotel_data["data"][:5]]
        selected_hotel = st.selectbox("Select a Hotel", hotel_options, key="hotel_selection")

        # Use session state to remember check-in and check-out dates
        if 'checkin_date' not in st.session_state:
            st.session_state.checkin_date = datetime.now().date()

        checkin_date = st.date_input("Check-in Date", min_value=datetime.now().date(), value=st.session_state.checkin_date, key="hotel_checkin")
        st.session_state.checkin_date = checkin_date

        # Automatically set check-out date to the check-in date if it's before
        if 'checkout_date' not in st.session_state or st.session_state.checkout_date < st.session_state.checkin_date:
            st.session_state.checkout_date = checkin_date + timedelta(days=1)  # Default to one day after check-in

        checkout_date = st.date_input("Check-out Date", min_value=checkin_date, value=st.session_state.checkout_date, key="hotel_checkout")
        st.session_state.checkout_date = checkout_date

        room_type = st.selectbox("Select Room Type", ["Single", "Double", "Suite", "Deluxe"], key="hotel_room")

        # Calculate price only if check-in and check-out are valid
        num_days = (checkout_date - checkin_date).days
        if num_days <= 0:
            st.error("Check-out date must be after check-in date and at least a one-night stay.")
        else:
            total_price = calculate_hotel_price(room_type, num_days)
            st.write(f"Total Price for {num_days} day(s) in a {room_type}: {total_price:.2f} INR")


            payment_method = st.radio("Select Payment Method", ["Credit Card", "Debit Card", "UPI"], key="hotel_payment")

            if st.button("Confirm Booking", key="confirm_hotel"):
                booking_details = {
                    "city": city,
                    "hotel": selected_hotel,
                    "checkin_date": str(checkin_date),
                    "checkout_date": str(checkout_date),
                    "room_type": room_type,
                    "total_price": total_price,
                    "payment_method": payment_method,
                    "booking_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                booking_id = store_booking('hotel', booking_details)
                st.success(f"Hotel booked successfully! Booking ID: {booking_id}")

# Car Booking Function
def car_booking():
    st.header("Car Rental Booking")
    
    # Select the city for car rentals
    city = st.selectbox("Select City", ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"], key="car_city")

    # Use session state to persist car data and selected car
    if 'car_data' not in st.session_state:
        st.session_state.car_data = None
    if 'selected_car' not in st.session_state:
        st.session_state.selected_car = None
    if 'car_details' not in st.session_state:
        st.session_state.car_details = None
    if 'dropoff_date' not in st.session_state:
        st.session_state.dropoff_date = None

    # Fetch car rentals when the user clicks the search button
    if st.button("Search Cars"):
        with st.spinner("Fetching car rental data..."):
            car_data = get_car_rentals(city)  # Search by location
            if car_data and car_data.get("data"):
                st.session_state.car_data = car_data
                st.session_state.selected_car = None  # Reset the selected car if the user re-searches
                cache_api_data('car', car_data)  # Cache the data to avoid multiple API calls
            else:
                st.error("No cars available for the selected city.")
                st.session_state.car_data = None

    # Ensure details are only shown after the user searches for cars
    if st.session_state.car_data and st.session_state.car_data.get("data"):
        # Show the car options with car name, vehicle number, and car ID
        car_options = [f"{car['brand']} - {car['name']} ({car['vehicleNumber']})" for car in st.session_state.car_data["data"][:15]]
        
        # Display car options after search
        selected_car_option = st.selectbox("Select a Car", car_options, key="car_selection")
        
        # Find the selected car's carId and display its details
        selected_car_index = car_options.index(selected_car_option)
        selected_car = st.session_state.car_data["data"][selected_car_index]
        car_id = selected_car["carId"]
        
        # Display the selected car's information
        st.write(f"**Car Brand:** {selected_car['brand']}")
        st.write(f"**Car Model:** {selected_car['name']}")
        st.write(f"**Vehicle Number:** {selected_car['vehicleNumber']}")
        st.write(f"**Price Per Day:** {selected_car['finalPrice']} INR")
        
        # Booking section
        pickup_date = st.date_input("Pick-up Date", min_value=datetime.now().date(), key="car_pickup")
        
        # Ensure the drop-off date is always after the pick-up date
        if st.session_state.dropoff_date is None or st.session_state.dropoff_date < pickup_date:
            st.session_state.dropoff_date = pickup_date + timedelta(days=1)  # Default drop-off date is one day after pick-up

        # Drop-off date input
        dropoff_date = st.date_input("Drop-off Date", min_value=pickup_date, value=st.session_state.dropoff_date, key="car_dropoff")
        st.session_state.dropoff_date = dropoff_date

        num_days = (dropoff_date - pickup_date).days

        if num_days > 0:
            total_price = selected_car['finalPrice'] * num_days
            st.write(f"**Total Price for {num_days} day(s):** {total_price:.2f} INR")
        else:
            st.error("Drop-off date must be at least one day after the pick-up date.")
            total_price = 0

        # Payment method
        payment_method = st.radio("Select Payment Method", ["Credit Card", "Debit Card", "UPI"], key="car_payment")

        # Confirm booking
        if st.button("Confirm Booking", key="confirm_car") and num_days > 0:
            booking_details = {
                "city": city,
                "car": f"{selected_car['brand']} {selected_car['name']} ({selected_car['vehicleNumber']})",
                "pickup_date": str(pickup_date),
                "dropoff_date": str(dropoff_date),
                "total_price": total_price,
                "payment_method": payment_method,
                "booking_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            booking_id = generate_booking_id('car')  # Generate a unique booking ID
            store_booking('car', booking_details)
            st.success(f"Car rental booked successfully! Booking ID: {booking_id}")

# Travel History and Cancellation Function
def travel_history():
    st.header("Travel History")
    
    if 'email' not in st.session_state:
        st.error("User email is not available. Please log in.")
        return

    # Active bookings table
    st.subheader("Active Bookings")
    user_email = st.session_state['email']  # Use logged-in user's email
    history = fetch_booking_history(user_email, canceled=0)
    if history:
        active_data = []
        cancelable_bookings = []
        for idx, record in enumerate(history):
            booking_id, service_type, details, booking_date = record
            booking_dict = eval(details)
            eligible_for_cancellation = "Yes" if is_within_24_hours(booking_dict.get("booking_datetime", "")) else "No"
            
            # Extract relevant details from the dictionary and format it
            if service_type == 'flight':
                formatted_details = (
                    f"Source: {booking_dict.get('source')}, "
                    f"Destination: {booking_dict.get('destination')}, "
                    f"Departure: {booking_dict.get('departure_date')}, "
                    f"Return: {booking_dict.get('return_date')}, "
                    f"Class: {booking_dict.get('travel_class')}, "
                    f"Flight: {booking_dict.get('selected_flight')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            elif service_type == 'hotel':
                formatted_details = (
                    f"Hotel: {booking_dict.get('hotel')}, "
                    f"City: {booking_dict.get('city')}, "
                    f"Check-in: {booking_dict.get('checkin_date')}, "
                    f"Check-out: {booking_dict.get('checkout_date')}, "
                    f"Room Type: {booking_dict.get('room_type')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            elif service_type == 'car':
                formatted_details = (
                    f"Car: {booking_dict.get('car')}, "
                    f"City: {booking_dict.get('city')}, "
                    f"Pick-up: {booking_dict.get('pickup_date')}, "
                    f"Drop-off: {booking_dict.get('dropoff_date')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            
            active_data.append({
                "Booking ID": booking_id,
                "Service": service_type.capitalize(),
                "Details": formatted_details,
                "Booked On": booking_date,
                "Eligible for Cancellation": eligible_for_cancellation
            })
            
            # Collect eligible bookings for the dropdown
            if eligible_for_cancellation == "Yes":
                cancelable_bookings.append((idx, booking_id))  # Store index for reference

        # Display the table of active bookings
        st.table(pd.DataFrame(active_data, columns=["Booking ID", "Service", "Details", "Booked On", "Eligible for Cancellation"]))

        # Dropdown for cancelable bookings
        if cancelable_bookings:
            cancel_option = st.selectbox(
                "Select a booking to cancel", 
                [f"{active_data[idx]['Service']} booking ID: {active_data[idx]['Booking ID']}" for idx, _ in cancelable_bookings]
            )
            
            # Extract the index of the selected option
            cancel_index = next(i for i, opt in enumerate(cancelable_bookings) if f"{active_data[opt[0]]['Service']} booking ID: {active_data[opt[0]]['Booking ID']}" == cancel_option)
            
            # Button to confirm cancellation
            if st.button("Confirm Cancellation"):
                cancel_booking(cancelable_bookings[cancel_index][1], user_email)  # Pass the user_email to cancel_booking
                st.success(f"Booking ID: {cancelable_bookings[cancel_index][1]} canceled.")
                st.stop()  # Stop script execution, re-render on next user interaction
        else:
            st.write("No bookings eligible for cancellation.")

    else:
        st.write("No active bookings found.")

    # Canceled bookings table
    st.subheader("Canceled Bookings")
    canceled_history = fetch_booking_history(user_email, canceled=1)
    if canceled_history:
        canceled_data = []
        for record in canceled_history:
            booking_id, service_type, details, booking_date = record
            booking_dict = eval(details)
            if service_type == 'flight':
                formatted_details = (
                    f"Source: {booking_dict.get('source')}, "
                    f"Destination: {booking_dict.get('destination')}, "
                    f"Departure: {booking_dict.get('departure_date')}, "
                    f"Return: {booking_dict.get('return_date')}, "
                    f"Class: {booking_dict.get('travel_class')}, "
                    f"Flight: {booking_dict.get('selected_flight')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            elif service_type == 'hotel':
                formatted_details = (
                    f"Hotel: {booking_dict.get('hotel')}, "
                    f"City: {booking_dict.get('city')}, "
                    f"Check-in: {booking_dict.get('checkin_date')}, "
                    f"Check-out: {booking_dict.get('checkout_date')}, "
                    f"Room Type: {booking_dict.get('room_type')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            elif service_type == 'car':
                formatted_details = (
                    f"Car: {booking_dict.get('car')}, "
                    f"City: {booking_dict.get('city')}, "
                    f"Pick-up: {booking_dict.get('pickup_date')}, "
                    f"Drop-off: {booking_dict.get('dropoff_date')}, "
                    f"Payment: {booking_dict.get('payment_method')}"
                )
            canceled_data.append({
                "Booking ID": booking_id,
                "Service": service_type.capitalize(),
                "Details": formatted_details,
                "Canceled On": booking_date
            })
        
        st.table(pd.DataFrame(canceled_data, columns=["Booking ID", "Service", "Details", "Canceled On"]))
    else:
        st.write("No canceled bookings found.")

# Main service selection
service_choice = st.selectbox("Select a service:", ["Flight", "Hotel", "Car Rental", "Travel History"], key="main_service")

if service_choice == "Flight":
    flight_booking()
elif service_choice == "Hotel":
    hotel_booking()
elif service_choice == "Car Rental":
    car_booking()
elif service_choice == "Travel History":
    travel_history()
