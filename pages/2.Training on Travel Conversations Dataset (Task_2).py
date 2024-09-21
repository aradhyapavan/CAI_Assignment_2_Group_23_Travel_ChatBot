import streamlit as st
import time
import login_signup
import os
import pandas as pd
from datetime import datetime, timedelta
import re
from utils import preprocess, extract_entities_with_bert, predict_intent_with_model, word_count, load_model, clean_entities, classify_entities

# Load datasets
@st.cache_resource
def load_data():
    car_rental_data = pd.read_csv('synthetic_car_rental_data.csv')
    flight_data = pd.read_csv('synthetic_flight_data.csv')
    hotel_data = pd.read_csv('synthetic_hotel_data.csv')
    travel_advisory_data = pd.read_csv('synthetic_travel_advisories.csv')
    return car_rental_data, flight_data, hotel_data, travel_advisory_data

car_rental_data, flight_data, hotel_data, travel_advisory_data = load_data()

model_path = 'travel_chatbot_model.pkl'

# Function to map intents to services
def map_intent_to_service(intent):
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
        "covid_restrictions": "Get COVID-19 travel restrictions",
    }
    return intent_service_map.get(intent, "Unknown service")

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

# Load training data
@st.cache_resource
def load_training_data():
    return pd.read_csv('synthetic_travel_conversations_for_training.csv')

training_data = load_training_data()

# Enhanced date extraction function
def extract_dates(query):
    """Extracts full dates, month-year combinations, week names, and relative time expressions."""
    dates = []
    months = []
    today = datetime.now()

    # Regex for explicit dates in the format YYYY-MM-DD
    date_pattern = r'\b(\d{4}-\d{2}-\d{2})\b'
    date_matches = re.findall(date_pattern, query)

    # Regex to identify month-year combinations like "August 2024"
    month_year_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b'
    month_year_matches = re.findall(month_year_pattern, query, re.IGNORECASE)

    # Add full date matches to the list
    for date_str in date_matches:
        dates.append(date_str)

    # Add month-year matches
    for month, year in month_year_matches:
        formatted_month_year = f"{month.capitalize()} {year}"
        months.append(formatted_month_year)

    # Handle month-only mentions like "in January"
    month_only_pattern = r'\b(in|on)?\s*(january|february|march|april|may|june|july|august|september|october|november|december)\b'
    month_only_matches = re.findall(month_only_pattern, query, re.IGNORECASE)

    for _, month in month_only_matches:
        months.append(month.capitalize())

    # Handle relative time expressions like "tomorrow", "next week", "next month"
    if "tomorrow" in query.lower():
        dates.append((today + timedelta(days=1)).strftime('%Y-%m-%d'))
    if "next week" in query.lower():
        dates.append((today + timedelta(weeks=1)).strftime('%Y-%m-%d'))
    if "next month" in query.lower():
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        dates.append(next_month.strftime('%Y-%m-%d'))

    # Handle "next X weeks" or "next X days"
    next_x_weeks = re.search(r'next (\d+) week', query, re.IGNORECASE)
    next_x_days = re.search(r'next (\d+) day', query, re.IGNORECASE)
    if next_x_weeks:
        weeks = int(next_x_weeks.group(1))
        dates.append((today + timedelta(weeks=weeks)).strftime('%Y-%m-%d'))
    if next_x_days:
        days = int(next_x_days.group(1))
        dates.append((today + timedelta(days=days)).strftime('%Y-%m-%d'))

    # Handle week day mentions like "next Monday"
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(weekdays):
        if f'next {day}' in query.lower():
            # Calculate the next occurrence of the given weekday
            days_ahead = i - today.weekday()
            if days_ahead <= 0:  # If the day is today or has already passed
                days_ahead += 7
            next_day = today + timedelta(days=days_ahead)
            dates.append(next_day.strftime('%Y-%m-%d'))

    return dates, months

# Clean dates and handle uniqueness
def clean_dates(dates, months):
    """Removes duplicate dates and formats them for display."""
    cleaned_dates = []
    seen_dates = set()

    # Add full dates (like "2025-01-10")
    for date_str in dates:
        if date_str not in seen_dates:
            seen_dates.add(date_str)
            cleaned_dates.append(f"**{date_str}** (Full Date)")

    # Add month-only matches (like "August 2024")
    for month_str in months:
        if month_str not in seen_dates:
            seen_dates.add(month_str)
            cleaned_dates.append(f"**{month_str}** (Month and Year)")

    return cleaned_dates


# Task 2: Training on Travel-Related Conversations
st.header("Task 2: Training on Travel-Related Conversations")

# Display the training dataset
st.subheader("Training Dataset Overview")
st.write("The chatbot has been trained on the following dataset:")
st.dataframe(training_data.head())

# Explanation of how the model was trained
st.write("""
### Model Training and Functionality:
The chatbot's intent classification model was trained using the **synthetic_travel_conversations_for_training.csv** dataset, which contains **5,000+ travel-related conversations** and corresponding intents. The dataset has a total shape of **(5000, 2)**, with each row representing a conversation and its corresponding intent.

The training involves the following steps:

1. **Preprocessing**: 
    - The input text was cleaned, tokenized, and lemmatized using the `preprocess()` function from the `utils.py` module. This step removes stopwords and reduces words to their base form using **spaCy**, ensuring that the model receives consistent input data.
   
2. **Vectorization**: 
    - Text data was transformed into numerical features using **TF-IDF (Term Frequency-Inverse Document Frequency)**. The `TfidfVectorizer` was used to convert the preprocessed text into feature vectors that represent the importance of words in the dataset.
   
3. **Intent Classification**: 
    - The chatbot uses a **Random Forest Classifier** for intent prediction. This model was trained to classify user queries into predefined intents such as `flight_booking`, `hotel_inquiry`, `car_rental`, etc.
    - The `train_and_save_model()` function in the `utils.py` module handles the model training, and the `predict_intent_with_model()` function is used to predict the intent based on user input.

4. **Entity Extraction**: 
    - Entities such as cities, airlines, car types, and dates are extracted from the query using advanced methods like **BERT Named Entity Recognition (NER)**, provided by the `extract_entities_with_bert()` function. This helps in identifying the relevant entities for generating accurate responses.

5. **Date Extraction**: 
    - Dates are extracted using the `extract_dates()` function, which combines **regular expressions** with the **dateparser** library to identify and standardize various date formats mentioned in the user queries (e.g., "next Monday", "in two weeks").
""")

if 'greeting_shown' not in st.session_state:
    with st.chat_message("assistant"):
        st.markdown(f"Hello {st.session_state['name']}! How can I assist you with your travel plans today?")
    st.session_state.greeting_shown = True

if 'conversation_history_task2' not in st.session_state:
    st.session_state.conversation_history_task2 = []

if 'model_loaded' not in st.session_state:
    st.session_state.model_loaded = False

@st.cache_resource(show_spinner=False)
def load_cached_model():
    if os.path.exists(model_path):
        time.sleep(1)
        vectorizer, intent_classifier = load_model()
        st.success("Model loaded successfully!")
    else:
        with st.spinner("Training model now... This may take a few moments."):
            vectorizer, intent_classifier = load_model()
        st.success("Model training completed!")
    return vectorizer, intent_classifier

def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

# Function to extract relevant data from the datasets
def extract_values_from_data(intent, query_input, locations, entities):
    if intent == "car_rental":
        matched_data = car_rental_data[car_rental_data['City'].str.lower().isin([loc.lower() for loc in locations])]
        if not matched_data.empty:
            car_type = matched_data['Car_Type'].iloc[0]
            return f"Car Type: {car_type}, City: {locations[0]}"
        else:
            return "No matching car rental data found."

    elif intent == "flight_booking":
        if 'Airline' in entities:
            matched_data = flight_data[flight_data['Source'].str.lower().isin([loc.lower() for loc in locations]) | flight_data['Destination'].str.lower().isin([loc.lower() for loc in locations])]
            if not matched_data.empty:
                airline = matched_data['Airline'].iloc[0]
                return f"Airline: {airline}, Source/Destination: {', '.join(locations)}"
        return "No matching flight data found."

    elif intent == "hotel_booking":
        if 'Room_Type' in entities or 'Hotel_Name' in entities:
            matched_data = hotel_data[hotel_data['City'].str.lower().isin([loc.lower() for loc in locations])]
            if not matched_data.empty:
                hotel_name = matched_data['Hotel_Name'].iloc[0]
                room_type = matched_data['Room_Type'].iloc[0]
                return f"Hotel Name: {hotel_name}, Room Type: {room_type}, City: {locations[0]}"
        return "No matching hotel data found."

    elif intent == "travel_advisory":
        matched_data = travel_advisory_data[travel_advisory_data['City'].str.lower().isin([loc.lower() for loc in locations])]
        if not matched_data.empty:
            advisory_level = matched_data['Advisory_Level'].iloc[0]
            reason = matched_data['Reason'].iloc[0]
            return f"Advisory Level: {advisory_level}, Reason: {reason}, City: {locations[0]}"
        else:
            return "No matching travel advisory data found."

    return "No matching data found for your query."

def chatbot_interface():
    if not st.session_state.get('model_loaded', False):
        with st.spinner("Initializing the chatbot, please wait..."):
            vectorizer, intent_classifier = load_cached_model()
            st.session_state.vectorizer = vectorizer
            st.session_state.intent_classifier = intent_classifier
            st.session_state.model_loaded = True

    # Display previous chat history
    for chat in st.session_state.get('conversation_history_task2', []):
        with st.chat_message(chat['role']):
            st.markdown(chat['message'])

    # Service selection dropdown
    service_option = st.selectbox(
        "What would you like to query about?", 
        ["Flight", "Hotel", "Car Rental", "Travel Advisory"]
    )

    # Show relevant example queries based on selected service
    if service_option == "Car Rental":
        st.markdown("""
        ### Example Queries for Car Rentals:
        - "I'd like to rent a convertible in Hyderabad on 2024-11-9."
        - "Can I rent an SUV in Bangalore ?"
        - "Are luxury cars available for rent in Mumbai?"
        - "I need to rent a convertible in Pune in July 2025."
        """)
    elif service_option == "Flight":
        st.markdown("""
        ### Example Queries for Flights:
        - "Can you help me book a flight from Jaipur to Chennai on 2025-01-10?"
        - "Is there a flight from Chennai to Kolkata in August 2024?"
        - "I want to book a flight from Chennai to Pune in January."
        """)
    elif service_option == "Hotel":
        st.markdown("""
        ### Example Queries for Hotels:
        - "I'd like to book a deluxe room in Chennai on 2025-06-12."
        - "Are there any double rooms available in Mumbai in December?"
        - "Can I book a Hotel room in Hyderabad on next week?"
        """)
    elif service_option == "Travel Advisory":
        st.markdown("""
        ### Example Queries for Travel Advisories:
        - "Are there any travel advisories for Delhi in June 2025?"
        - "What's the travel advisory for Bangalore in October 2024?"
        - "Any travel warnings for Jaipur in June 2025?"
        """)

    # Handle user input dynamically
    query_input = st.chat_input("What's your travel query?")
    
    if query_input:
        if word_count(query_input) < 4:
            st.warning("Please enter a more detailed query (at least 4 words).")
            return

        st.session_state.conversation_history_task2.append({"role": "user", "message": query_input})

        with st.chat_message("user"):
            st.markdown(query_input)

        with st.spinner("Processing your request..."):
            time.sleep(1)

            # Predict the intent
            intent = predict_intent_with_model(query_input, st.session_state.vectorizer, st.session_state.intent_classifier)
            service = map_intent_to_service(intent)

            # Debug: Add intent and service information to chat for debugging
            st.write(f"Predicted Intent: {intent}")
            st.write(f"Mapped Service: {service}")

            entities, locations = extract_entities_with_bert(query_input)
            date_result, month_result = extract_dates(query_input)
            cleaned_dates = clean_dates(date_result, month_result)

            # Generate bot reply with highlighted parts
            bot_reply = f"Thank you! You are interested in **{service}** (Intent: {intent})."

            # Handle locations and dates for flights, hotels, car rentals, and advisories
            if locations:
                bot_reply += f" You've mentioned the following **locations**: {', '.join(f'**{loc}**' for loc in locations)}."
            if cleaned_dates:
                bot_reply += f" The **date(s)** you've mentioned: {', '.join(cleaned_dates)}."

            # Clean up extracted entities (like car type, hotel type, etc.)
            classified_entities = classify_entities(entities, locations)

            if classified_entities:
                bot_reply += f" The **entities** identified are: {classified_entities}."

            # Extract relevant values from the dataset based on the intent and locations, but only show relevant details
            extracted_values = extract_values_from_data(intent, query_input, locations, classified_entities)

            # Append relevant data to the bot reply
            if extracted_values:
                bot_reply += f" Relevant data: {extracted_values}"

            # Append the bot's reply to the conversation history
            st.session_state.conversation_history_task2.append({"role": "bot", "message": bot_reply})

            with st.chat_message("assistant"):
                response = st.write_stream(response_generator(bot_reply))

            # Display the detected information in a table, focusing on the exact entities and values that the user mentioned
            st.markdown("### Detected Information")
            st.table({
                "Predicted Intent": [intent],
                "Mapped Service": [service],
                "Extracted Entities": [classified_entities],
                "Extracted Locations": [', '.join(locations)],
                "Extracted Dates": [', '.join(cleaned_dates if cleaned_dates else [])],
                "Extracted Values": [extracted_values]
            })

        # Show more examples at the bottom to assist users with queries based on the service_option
        if service_option == "Car Rental":
            st.markdown("""
            ### Example Queries for Car Rentals:
            - "I'd like to rent a convertible in Hyderabad on November 20, 2024."
            - "Can I rent an SUV in Bangalore in December?"
            - "Are luxury cars available for rent in Mumbai?"
            - "I need to rent a convertible in Pune in July 2025."
            """)
        elif service_option == "Flight":
            st.markdown("""
            ### Example Queries for Flights:
            - "Can you help me book a flight from Jaipur to Chennai on January 23, 2025?"
            - "Is there a flight from Chennai to Kolkata in August 2025?"
            - "I want to book a flight from Chennai to Pune in January."
            """)
        elif service_option == "Hotel":
            st.markdown("""
            ### Example Queries for Hotels:
            - "I'd like to book a deluxe room in Chennai on August 1, 2025."
            - "Are there any double rooms available in Mumbai in December?"
            - "Can I book a room in Hyderabad on December 31?"
            """)
        elif service_option == "Travel Advisory":
            st.markdown("""
            ### Example Queries for Travel Advisories:
            - "Are there any travel advisories for Delhi in June 2025?"
            - "What's the travel advisory for Bangalore in October 2024?"
            - "Any travel warnings for Jaipur in June 2025?"
            """)

# Chatbot interface function
chatbot_interface()

# Provide a logout button in the sidebar
if st.sidebar.button("Logout"):
    login_signup.logout()
