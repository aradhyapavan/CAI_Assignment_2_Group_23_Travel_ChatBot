import streamlit as st
import time
import login_signup
import os
import re
from utils import preprocess, extract_entities_with_bert, predict_intent, word_count, load_model, clean_entities
from datetime import datetime, timedelta

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
        st.stop()  # Stop further execution until the user logs in

check_login()

# Now, if the user is logged in, proceed with the chatbot interface
st.title("Travel Chatbot - Task 1: Natural Language Understanding")


# Model training information for Task 1
st.markdown("""
### Task Overview
In this task, the chatbot focuses on understanding travel-related terminologies and extracting intents, services, locations, and dates from user queries.

### Model Training Information
This chatbot uses a machine learning model trained on travel-related intents and entities. It has been trained using a diverse dataset to accurately interpret user queries and provide relevant information.

The model is designed to:
- **Identify user intents** such as booking flights, checking status, or getting travel advisories.
- **Extract relevant entities** like locations and dates from user queries.

### Current Capabilities
1. **Intent Recognition**: Understand what the user wants to do (e.g., book a flight).
2. **Entity Extraction**: Identify important details from the user’s input, such as destination and travel dates.
3. **Response Generation**: Provide coherent responses based on the user's input and the recognized intents and entities.
""")

if 'greeting_shown' not in st.session_state:
    with st.chat_message("assistant"):
        st.markdown(f"Hello {st.session_state['name']}! How can I assist you with your travel plans today?")
    st.session_state.greeting_shown = True

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'model_loaded' not in st.session_state:
    st.session_state.model_loaded = False
if 'examples_shown' not in st.session_state:
    st.session_state.examples_shown = False
if 'selected_service' not in st.session_state:
    st.session_state.selected_service = None

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

# Custom date extraction logic (without dateparser)
def extract_dates(query):
    """Extracts full dates (YYYY-MM-DD), month mentions, week names, and relative time expressions."""
    dates = []
    months = []
    today = datetime.now()

    # Regex for explicit dates in the format YYYY-MM-DD
    date_pattern = r'\b(\d{4}-\d{2}-\d{2})\b'
    date_matches = re.findall(date_pattern, query)

    # Regex to identify month names
    month_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b'
    month_matches = re.findall(month_pattern, query, re.IGNORECASE)

    # Add full date matches to the list
    for date_str in date_matches:
        dates.append(date_str)

    # Add month-only matches to the months list
    for month in month_matches:
        months.append(month.capitalize())

    # Handle relative time expressions like "tomorrow", "next week", "next 2 weeks", "next Monday"
    if "tomorrow" in query.lower():
        dates.append((today + timedelta(days=1)).strftime('%Y-%m-%d'))
    if "next week" in query.lower():
        dates.append((today + timedelta(weeks=1)).strftime('%Y-%m-%d'))
    if "next month" in query.lower():
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        dates.append(next_month.strftime('%Y-%m-%d'))

    # Handle "next [x] weeks" or "next [x] days"
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
            days_ahead = i - today.weekday()
            if days_ahead <= 0:  # If the day is today or has already passed
                days_ahead += 7
            next_day = today + timedelta(days=days_ahead)
            dates.append(next_day.strftime('%Y-%m-%d'))

    return dates, months

# Clean dates and handle uniqueness
def clean_dates(dates, months):
    """Remove duplicate dates and handle full date vs month-only mentions."""
    cleaned_dates = []
    seen_dates = set()

    # Add full dates (like "2025-01-10")
    for date_obj in dates:
        if date_obj not in seen_dates:
            seen_dates.add(date_obj)
            cleaned_dates.append(f"**{date_obj}** (Full Date)")

    # Add month-only mentions (like "January")
    for month in months:
        if month not in cleaned_dates:  # Prevent duplication with full dates
            cleaned_dates.append(f"**{month}** (Month)")

    return cleaned_dates

# Show relevant examples based on service selected
def show_examples(service_option):
    """Show relevant example queries based on selected service."""
    
    if service_option == "Flight":
        st.markdown("""
        ### Example Queries for Flights:
        1. "Can you help me book a flight from Mumbai to Delhi on 2024-12-12?"
        2. "What is the status of flight AI202 from Kolkata to Chennai?"
        3. "I need to cancel my flight to Bangalore."
        4. "Can I change my flight from Hyderabad to Jaipur in January ?"
        5. "I want to book a flight from Chennai to Pune on next Monday"
        """)
    
    elif service_option == "Hotel":
        st.markdown("""
        ### Example Queries for Hotels:
        1. "I'd like to book a Deluxe room in Chennai for next weekend."
        2. "Are there any available hotels in Bangalore from March 5 to March 10, 2025?"
        3. "Can I upgrade my room at the hotel in Pune?"
        4. "What amenities does the hotel in Jaipur offer?"
        5. "I need to cancel my hotel reservation in Kolkata."
        """)
    
    elif service_option == "Car Rental":
        st.markdown("""
        ### Example Queries for Car Rentals:
        1. "Can I rent an SUV in Delhi on February 15, 2025?"
        2. "What is the price for a Luxury car rental in Mumbai?"
        3. "Is a Sedan available for rent in Chennai?"
        4. "Can I extend my Hatchback rental in Bangalore for another week?"
        5. "Are luxury cars available for rent in Hyderabad?"
        """)
    
    elif service_option == "Travel Advisory":
        st.markdown("""
        ### Example Queries for Travel Advisories:
        1. "What are the travel advisories for Pune?"
        2. "Is there a weather advisory for Delhi?"
        3. "Are there any health advisories for Kolkata?"
        4. "Is there political unrest in Jaipur?"
        5. "What are the COVID restrictions in Mumbai?"
        """)

def chatbot_interface():
    if not st.session_state.model_loaded:
        with st.spinner("Initializing the chatbot, please wait..."):
            vectorizer, intent_classifier = load_cached_model()
            st.session_state.vectorizer = vectorizer
            st.session_state.intent_classifier = intent_classifier
            st.session_state.model_loaded = True

    for chat in st.session_state.conversation_history:
        with st.chat_message(chat['role']):
            st.markdown(chat['message'])

    # Dropdown for service options (Flight, Hotel, Car Rental, Travel Advisory)
    service_option = st.selectbox(
        "What would you like to query about?", 
        ["Flight", "Hotel", "Car Rental", "Travel Advisory"]
    )

    # Show examples when service is changed or after bot response
    if st.session_state.selected_service != service_option:
        st.session_state.examples_shown = False  # Reset examples to be shown again
        st.session_state.selected_service = service_option  # Update selected service

    # Show examples for the selected service if no conversation history exists or dropdown changes
    if not st.session_state.conversation_history or not st.session_state.examples_shown:
        show_examples(service_option)
        st.session_state.examples_shown = True  # Ensure examples aren't shown repeatedly

    if query_input := st.chat_input("What's your travel query?"):
        if word_count(query_input) < 4:
            st.warning("Please enter a more detailed query (at least 4 words).")
            return

        st.session_state.conversation_history.append({"role": "user", "message": query_input})

        with st.chat_message("user"):
            st.markdown(query_input)

        with st.spinner("Processing your request..."):
            time.sleep(1)

            intent = predict_intent(query_input)
            service = map_intent_to_service(intent)
            entities, locations = extract_entities_with_bert(query_input)

            # Extract full dates, months, and relative time expressions
            date_result, month_result = extract_dates(query_input)
            cleaned_dates = clean_dates(date_result, month_result)

            # Generate bot reply
            bot_reply = f"Thank you! You are interested in **{service}** (Intent: {intent})."

            if locations:
                bot_reply += f" You've mentioned the following **locations**: {', '.join(f'**{loc}**' for loc in locations)}."
            if cleaned_dates:
                bot_reply += f" The **date(s)** you've mentioned: {', '.join(cleaned_dates)}."
            else:
                bot_reply += " No valid dates were identified."

            cleaned_entities = clean_entities(entities)
            if cleaned_entities:
                bot_reply += f" The **entities** identified are: {', '.join(cleaned_entities)}."

            st.session_state.conversation_history.append({"role": "bot", "message": bot_reply})

            with st.chat_message("assistant"):
                response = st.write_stream(response_generator(bot_reply))

            # Reset examples to show for the selected service after the bot response
            st.session_state.examples_shown = False
            show_examples(service_option)

            # Update the table to include the service (intent)
            st.markdown("### Detected Information")
            st.table({
                "Predicted Intent": [intent],
                "Mapped Service": [service],
                "Extracted Entities": [', '.join(cleaned_entities)],
                "Extracted Locations": [', '.join(locations)],
                "Extracted Dates": [', '.join(cleaned_dates if cleaned_dates else [])]
            })

chatbot_interface()

# Logout button
if st.sidebar.button("Logout"):
    login_signup.logout()
