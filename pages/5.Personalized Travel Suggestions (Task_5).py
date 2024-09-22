import streamlit as st
import pandas as pd
from utils import create_connection, fetch_amadeus_recommendations,get_flight_offers
import login_signup
import random

# IATA Code Mapping for Major Cities
city_to_iata = {
    'Mumbai': 'BOM',
    'Delhi': 'DEL',
    'Bangalore': 'BLR',
    'Hyderabad': 'HYD',
    'Chennai': 'MAA',
    'Kolkata': 'CCU',
    'Pune': 'PNQ',
    'Jaipur': 'JAI'
}

# Traveler origin country (e.g., IN for India)
traveler_country_code = 'IN'  # Modify if needed

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



# Greeting and Overview of Recommendations
st.title("🤖 Welcome to Your Travel Recommendations!")
if 'name' in st.session_state:
    st.markdown(f"Hello, {st.session_state['name']}! I'm here to provide you with personalized travel recommendations based on your past searches and preferences.")
else:
    st.markdown("Hello! I'm here to provide you with personalized travel recommendations based on your history and preferences.")

st.markdown("""
### 🌟 How We Provide Recommendations:
- We analyze your **previous searches** for flights, hotels, car rentals, and travel advisories.
- Based on your **most frequently searched locations** and intents, we suggest:
    - **Flight recommendations** from your commonly searched city pairs or destinations.
    - **Hotel options** in cities you've previously shown interest in.
    - **Car rental services** in locations you've inquired about.
    - **Travel advisories** to keep you informed about potential issues at your destinations.
- Our system also includes **random suggestions** to enhance your travel experience, such as exploring nearby attractions or trying local cuisine!

Let's dive into your tailored travel suggestions! Select an option below or view the recommendations generated from your travel history.
""")


# Connect to the database
conn = create_connection()
cursor = conn.cursor()

# Query stored user data from the user_queries table
cursor.execute("SELECT * FROM user_queries")
stored_queries = cursor.fetchall()

# Assuming the columns as 'user_query', 'intent', 'locations', and 'dates'
stored_queries_df = pd.DataFrame(stored_queries, columns=['id', 'user_query', 'intent', 'locations', 'dates'])

# Load external data files for flight, hotel, car rental, travel advisory, and recommendations
flight_df = pd.read_csv("synthetic_flight_data.csv")
hotel_df = pd.read_csv("synthetic_hotel_data.csv")
car_rental_df = pd.read_csv("synthetic_car_rental_data.csv")
travel_advisory_df = pd.read_csv("synthetic_travel_advisories.csv")
recommendations_df = pd.read_csv("large_user_recommendations.csv")

# Ensure columns match expected values in recommendations dataframe
recommendations_df.columns = recommendations_df.columns.str.lower()

# Randomized suggestion generator for natural responses
def get_random_suggestion():
    suggestions = [
        "Explore the local cuisine and make the most of your visit!",
        "Discover hidden gems around your destination.",
        "We recommend checking out historical sites nearby!",
        "Consider upgrading to a premium flight experience.",
        "Why not explore some nearby attractions while you're there?",
        "Try a cultural or adventure activity for a change!"
    ]
    return random.choice(suggestions)

# Function to fetch most common location for a specific intent type
def get_most_common_location(stored_queries_df, intent_list):
    filtered_queries = stored_queries_df[stored_queries_df['intent'].isin(intent_list)]
    if not filtered_queries.empty:
        return filtered_queries['locations'].value_counts().idxmax()  # Most searched location
    return None

# Function to recommend based on user history, with conversational responses
def recommend_based_on_user_history(stored_queries_df):
    flight_intents = ['flight_booking', 'flight_inquiry', 'flight_cancellation', 'flight_status', 'flight_change']
    hotel_intents = ['hotel_booking', 'hotel_inquiry', 'hotel_cancellation', 'hotel_upgrade', 'hotel_amenities']
    car_rental_intents = ['car_rental', 'car_inquiry', 'car_cancellation', 'car_extension', 'car_price']
    advisory_intents = ['travel_advisory', 'weather_advisory', 'health_advisory', 'political_unrest_advisory', 'covid_restrictions']

    # Fetch most common locations based on intent types
    most_common_flight_location = get_most_common_location(stored_queries_df, flight_intents)
    most_common_hotel_location = get_most_common_location(stored_queries_df, hotel_intents)
    most_common_car_rental_location = get_most_common_location(stored_queries_df, car_rental_intents)
    most_common_advisory_location = get_most_common_location(stored_queries_df, advisory_intents)

    # Display a chat message like in your example
    with st.chat_message("assistant"):
        st.markdown(f"Hello {st.session_state['name']}! Based on your frequent searches, I have some personalized travel recommendations for you.")

    # Flight Recommendations (Handling city pairs)
    if most_common_flight_location and ',' in most_common_flight_location:
        origin, destination = most_common_flight_location.split(', ')
        with st.chat_message("assistant"):
            st.markdown(f"**Flight Recommendations from {origin} to {destination}:**")
        flight_recommendations = flight_df[
            (flight_df['Source'].str.lower() == origin.lower()) &
            (flight_df['Destination'].str.lower() == destination.lower())
        ].head(3)
        if not flight_recommendations.empty:
            for _, flight in flight_recommendations.iterrows():
                with st.chat_message("assistant"):
                    st.markdown(f"""
                    It looks like you're frequently flying from **{origin}** to **{destination}**! Here's a recommendation:
                    - **Airline**: {flight['Airline']}  
                    - **Route**: {flight['Source']} to {flight['Destination']}  
                    - **Date**: {flight['Date_of_Journey']}  
                    - **Price**: ₹{flight['Price']}  
                    - **Duration**: {flight['Duration']}  
                    - **Stops**: {flight['Total_Stops']}  
                    - **Arrival Time**: {flight['Arrival_Time']}  
                    {get_random_suggestion()}
                    ---""")
        else:
            with st.chat_message("assistant"):
                st.write(f"Sorry, no flights found from {origin} to {destination}.")

    elif most_common_flight_location:
        with st.chat_message("assistant"):
            st.markdown(f"**Flight Recommendations for {most_common_flight_location}:**")
        flight_recommendations = flight_df[flight_df['Destination'].str.lower() == most_common_flight_location.lower()].head(3)
        if not flight_recommendations.empty:
            for _, flight in flight_recommendations.iterrows():
                with st.chat_message("assistant"):
                    st.markdown(f"""
                    It looks like you're frequently flying to **{most_common_flight_location}**! Here's a recommendation:
                    - **Airline**: {flight['Airline']}  
                    - **Route**: {flight['Source']} to {flight['Destination']}  
                    - **Date**: {flight['Date_of_Journey']}  
                    - **Price**: ₹{flight['Price']}  
                    - **Duration**: {flight['Duration']}  
                    - **Stops**: {flight['Total_Stops']}  
                    - **Arrival Time**: {flight['Arrival_Time']}  
                    {get_random_suggestion()}
                    ---""")
        else:
            with st.chat_message("assistant"):
                st.write(f"Sorry, no flights to {most_common_flight_location} found in the current database.")

    # Hotel Recommendations
    if most_common_hotel_location:
        with st.chat_message("assistant"):
            st.markdown(f"**Hotel Recommendations for {most_common_hotel_location}:**")
        hotel_recommendations = hotel_df[hotel_df['City'].str.lower() == most_common_hotel_location.lower()].head(3)
        if not hotel_recommendations.empty:
            for _, hotel in hotel_recommendations.iterrows():
                with st.chat_message("assistant"):
                    st.markdown(f"""
                    Since you've been looking for hotels in **{most_common_hotel_location}**, I recommend the following option:
                    - **Hotel Name**: {hotel['Hotel_Name']}  
                    - **Room Type**: {hotel['Room_Type']}  
                    - **Price**: ₹{hotel['Price_Per_Night']} per night  
                    - **Check-In**: {hotel['Check_In_Date']}  
                    - **Availability**: {hotel['Availability_Status']}  
                    {get_random_suggestion()}
                    ---""")
        else:
            with st.chat_message("assistant"):
                st.write(f"No hotels found in {most_common_hotel_location}.")

    # Car Rental Recommendations
    if most_common_car_rental_location:
        with st.chat_message("assistant"):
            st.markdown(f"**Car Rental Recommendations for {most_common_car_rental_location}:**")
        car_rental_recommendations = car_rental_df[car_rental_df['City'].str.lower() == most_common_car_rental_location.lower()].head(3)
        if not car_rental_recommendations.empty:
            for _, car in car_rental_recommendations.iterrows():
                with st.chat_message("assistant"):
                    st.markdown(f"""
                    For car rentals in **{most_common_car_rental_location}**, you might like this:
                    - **Rental Company**: {car['Car_Rental_Company']}  
                    - **Car Type**: {car['Car_Type']}  
                    - **Price**: ₹{car['Price_Per_Day']} per day  
                    - **Pick-Up Date**: {car['Pickup_Date']}  
                    {get_random_suggestion()}
                    ---""")
        else:
            with st.chat_message("assistant"):
                st.write(f"No car rentals found in {most_common_car_rental_location}.")

    # Travel Advisory Recommendations
    # Travel Advisory Recommendations
    if most_common_advisory_location:
        with st.chat_message("assistant"):
            st.markdown(f"**Travel Advisories for {most_common_advisory_location}:**")
        advisory_recommendations = travel_advisory_df[travel_advisory_df['City'].str.lower() == most_common_advisory_location.lower()].head(3)
        if not advisory_recommendations.empty:
            for _, advisory in advisory_recommendations.iterrows():
                with st.chat_message("assistant"):
                    st.markdown(f"""
                    Here are some important advisories for **{most_common_advisory_location}**:
                    - **Advisory Level**: {advisory['Advisory_Level']}  
                    - **Reason**: {advisory['Reason']}  
                    - **Affected Routes**: {advisory['Affected_Routes']}  
                    - **Validity**: {advisory['Validity']}  
                    {get_random_suggestion()}
                    ---""")
        else:
            with st.chat_message("assistant"):
                st.write(f"No travel advisories found for {most_common_advisory_location}.")

    # General Recommendations based on user location and intent
    with st.chat_message("assistant"):
        st.write("### General Recommendations Based on Location and Intent")
    random_recommendations = recommendations_df.sample(n=3)
    if not random_recommendations.empty:
        for _, rec in random_recommendations.iterrows():
            with st.chat_message("assistant"):
                st.markdown(f"""
                I have a few more general recommendations for you:
                - **Location**: {rec['locations']}  
                - **Intent**: {rec['intent']}  
                - **Details**: {rec['recommendation']}  
                {get_random_suggestion()}
                ---""")
    else:
        with st.chat_message("assistant"):
            st.write("No additional general recommendations at the moment.")

# Recommend based on user's query history
recommend_based_on_user_history(stored_queries_df)

# Commit and close the connection
conn.commit()
conn.close()
