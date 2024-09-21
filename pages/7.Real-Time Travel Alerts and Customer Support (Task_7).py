import streamlit as st
import time
import logging
import os
import login_signup
from utils import get_flight_updates, get_customer_support, get_amadeus_token
from datetime import date

# Predefined cities and their airport codes
airport_codes = {
    'Mumbai': 'BOM',
    'Delhi': 'DEL',
    'Bangalore': 'BLR',
    'Hyderabad': 'HYD',
    'Chennai': 'MAA',
    'Kolkata': 'CCU',
    'Pune': 'PNQ',
    'Jaipur': 'JAI'
}

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

# Greeting message
st.title("✈️ Real-Time Travel Updates and Customer Support")
st.markdown("Hello! I'm here to assist you with real-time flight updates and comprehensive customer support.")

# Overview of features
st.markdown("""
### 📅 Real-Time Travel Updates
- Get the latest information on flight delays and gate changes for your selected airports.
- Stay informed about your travel plans with accurate and timely updates.

### 🤝 Customer Support
- Access support for any travel-related inquiries.
- Contact our support team via email, phone, or live chat.
- Explore frequently asked questions (FAQs) for quick assistance.

Let's check your flight updates!
""")

# Real-time travel updates
st.header("Flight Delays and Gate Changes")

# Select source and destination airports
source_city = st.selectbox("Select Source City", list(airport_codes.keys()))
destination_city = st.selectbox("Select Destination City", list(airport_codes.keys()))

# Select travel date, restrict to today and future dates
travel_date = st.date_input("Select your travel date", value=date.today(), min_value=date.today())

# Fetch airport codes based on selection
source_airport_code = airport_codes[source_city]
destination_airport_code = airport_codes[destination_city]

# Ensure source and destination are different
if source_city == destination_city:
    st.error("Source and destination cities cannot be the same.")
else:
    if st.button("Check Flight Updates"):
        st.write(f"Fetching flight updates for {travel_date}...")  # Show loading status
        logging.info(f"Checking flight updates for {travel_date}...")  # Log info for terminal

        try:
            # Fetch flight updates for source and destination airports on the selected date
            num_delayed_source, num_gate_changes_source, delayed_flights_source, gate_changes_source = get_flight_updates(source_airport_code, travel_date)
            num_delayed_destination, num_gate_changes_destination, delayed_flights_destination, gate_changes_destination = get_flight_updates(destination_airport_code, travel_date)

            # Debugging: Print fetched data for source and destination
            st.text(f"Source ({source_city}) on {travel_date}: Delayed Flights: {num_delayed_source}, Gate Changes: {num_gate_changes_source}")
            st.text(f"Destination ({destination_city}) on {travel_date}: Delayed Flights: {num_delayed_destination}, Gate Changes: {num_gate_changes_destination}")

            # Display results for source airport
            st.subheader(f"Flight Updates for {source_city} ({source_airport_code}) on {travel_date}")
            if num_delayed_source > 0:
                st.success(f"{num_delayed_source} flights have delays at {source_city} airport.")
                for flight in delayed_flights_source:
                    st.write(f"Flight {flight['flightNumber']} - Delay: {flight['delay']}, Gate Change: {flight.get('gateChange', 'None')}")
            else:
                st.info(f"No flight delays found for {source_city} airport on {travel_date}.")

            if num_gate_changes_source > 0:
                st.success(f"{num_gate_changes_source} flights have gate changes at {source_city} airport.")
            else:
                st.info(f"No gate changes found for {source_city} airport.")

            # Display results for destination airport
            st.subheader(f"Flight Updates for {destination_city} ({destination_airport_code}) on {travel_date}")
            if num_delayed_destination > 0:
                st.success(f"{num_delayed_destination} flights have delays at {destination_city} airport.")
                for flight in delayed_flights_destination:
                    st.write(f"Flight {flight['flightNumber']} - Delay: {flight['delay']}, Gate Change: {flight.get('gateChange', 'None')}")
            else:
                st.info(f"No flight delays found for {destination_city} airport on {travel_date}.")

            if num_gate_changes_destination > 0:
                st.success(f"{num_gate_changes_destination} flights have gate changes at {destination_city} airport.")
            else:
                st.info(f"No gate changes found for {destination_city} airport.")

        except Exception as e:
            logging.error(f"Error fetching flight updates: {str(e)}")
            st.error("Failed to fetch flight updates. Please try again later.")

# Customer support section
st.header("Customer Support")
support_info = get_customer_support()

st.subheader("Contact Us")
st.write(f"**Email:** {support_info['email']}")
st.write(f"**Phone:** {support_info['phone']}")
st.write(f"**Live Chat:** [Chat with us]({support_info['live_chat']})")
st.write(f"**FAQs:** [Frequently Asked Questions]({support_info['faq']})")

# FAQs Section
st.header("❓ Frequently Asked Questions (FAQs)")
st.markdown("""
- **Q: What services does the travel chatbot provide?**  
  A: Our chatbot assists with flight bookings, hotel reservations, car rentals, and travel advisories.

- **Q: How can I check flight updates?**  
  A: You can select your source and destination airports, along with your travel date, to get real-time flight updates.

- **Q: How do I contact customer support?**  
  A: You can reach us via email, phone, or live chat. Our contact details are provided above.

- **Q: Can I cancel my booking through the chatbot?**  
  A: Yes, you can manage your bookings, including cancellations, by interacting with the chatbot.

- **Q: Is there a way to see my booking history?**  
  A: Yes, you can view your past bookings through the travel history section in the chatbot.

- **Q: What should I do if I have an urgent travel issue?**  
  A: Please contact our customer support team immediately for assistance.
""")

# Logout button
if st.sidebar.button("Logout"):
    # Logic to log out the user
    st.session_state['logged_in'] = False
    st.success("You have been logged out.")
