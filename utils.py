import spacy
import re
import joblib
import os
import pandas as pd
from flair.data import Sentence
from flair.models import SequenceTagger
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from pyspark.ml import Pipeline
from sparknlp.base import DocumentAssembler
from sparknlp.annotator import Tokenizer, SentenceDetector, NerDLModel, NerConverter
from pyspark.sql import SparkSession
from dateparser.search import search_dates
from datetime import datetime, timedelta
import sparknlp
import streamlit as st

amadeus_client_id = st.secrets["AMADEUS_CLIENT_ID"]
amadeus_client_secret = st.secrets["AMADEUS_CLIENT_SECRET"]

import spacy.cli

# Download the SpaCy model if not already installed
spacy.cli.download("en_core_web_md")




# Load spaCy model
def load_spacy_model():
    return spacy.load("en_core_web_md")

nlp = load_spacy_model()

# Load BERT NER model
def load_ner_model():
    return pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

ner_model = load_ner_model()

# Load Flair model for date extraction
def load_flair_model():
    return SequenceTagger.load("flair/ner-english")

flair_tagger = load_flair_model()

# Initialize Spark NLP
def start_spark_nlp():
    return sparknlp.start()

# Extract dates using dateparser

import re
from dateparser.search import search_dates
from datetime import datetime, timedelta

# Enhanced date extraction function
def extract_dates(query):
    weeknames = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    results = search_dates(query)
    formatted_dates = []
    
    # Additional logic for parsing special cases
    next_x_weeks_match = re.search(r'next (\d+) week', query, re.IGNORECASE)
    next_x_months_match = re.search(r'next (\d+) month', query, re.IGNORECASE)
    next_x_weekday_match = re.search(r'next (\d+) (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', query, re.IGNORECASE)
    single_next_weekday_match = re.search(r'next (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', query, re.IGNORECASE)

    if results:
        for date_str, date_obj in results:
            # Handle "tomorrow"
            if "tomorrow" in date_str.lower():
                date_obj = datetime.now() + timedelta(days=1)
            elif "next week" in date_str.lower() or next_x_weeks_match:
                weeks_to_add = int(next_x_weeks_match.group(1)) if next_x_weeks_match else 1
                date_obj = datetime.now() + timedelta(weeks=weeks_to_add)
            elif "next month" in date_str.lower() or next_x_months_match:
                months_to_add = int(next_x_months_match.group(1)) if next_x_months_match else 1
                next_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1)
                for _ in range(months_to_add - 1):
                    next_month = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1)
                date_obj = next_month
            elif "next year" in date_str.lower():
                date_obj = datetime.now().replace(year=datetime.now().year + 1)
            elif single_next_weekday_match or next_x_weekday_match:
                weekdays_to_add = 1
                if next_x_weekday_match:
                    weekdays_to_add = int(next_x_weekday_match.group(1))
                    day_of_week = weeknames.index(next_x_weekday_match.group(2).lower())
                else:
                    day_of_week = weeknames.index(single_next_weekday_match.group(1).lower())
                    
                current_day_of_week = datetime.now().weekday()
                if day_of_week <= current_day_of_week:
                    date_obj = datetime.now() + timedelta(days=(7 - current_day_of_week + day_of_week) + (weekdays_to_add - 1) * 7)
                else:
                    date_obj = datetime.now() + timedelta(days=(day_of_week - current_day_of_week))
            formatted_dates.append((date_str, date_obj))

    return formatted_dates



# Extract named entities using Spark NLP
def extract_entities_spark_nlp(queries):
    spark = start_spark_nlp()
    data = spark.createDataFrame([[q] for q in queries]).toDF("text")
    
    # Define Spark NLP pipeline
    document_assembler = DocumentAssembler().setInputCol("text").setOutputCol("document")
    sentence_detector = SentenceDetector().setInputCols(["document"]).setOutputCol("sentences")
    tokenizer = Tokenizer().setInputCols(["sentences"]).setOutputCol("tokens")
    ner_dl = NerDLModel.pretrained("ner_dl", "en").setInputCols(["document", "tokens"]).setOutputCol("ner")
    ner_converter = NerConverter().setInputCols(["document", "tokens", "ner"]).setOutputCol("ner_chunk")

    pipeline = Pipeline(stages=[document_assembler, sentence_detector, tokenizer, ner_dl, ner_converter])
    model = pipeline.fit(data)
    results = model.transform(data)

    return results.select("text", "ner_chunk.result").collect()

# Preprocess text
def preprocess(text):
    # Remove non-alphabetical characters, convert to lowercase, remove stopwords, and lemmatize
    text = re.sub(r'\W+', ' ', text)
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
    return ' '.join(tokens)

# Load synthetic travel conversations dataset
def load_training_data():
    return pd.read_csv("synthetic_travel_conversations_for_training.csv")

# Train Naive Bayes model and save it
from sklearn.linear_model import LogisticRegression

def train_and_save_model(X, y):
    vectorizer = TfidfVectorizer(max_features=1500)
    X_tfidf = vectorizer.fit_transform(X)
    intent_classifier = LogisticRegression(max_iter=1000)
    intent_classifier.fit(X_tfidf, y)
    joblib.dump((vectorizer, intent_classifier), "travel_chatbot_model.pkl")
    return vectorizer, intent_classifier


# Load model from disk or train if unavailable
def load_model():
    if os.path.exists("travel_chatbot_model.pkl"):
        return joblib.load("travel_chatbot_model.pkl")
    else:
        df = load_training_data()
        X = df['conversation'].apply(preprocess)
        y = df['intent']
        return train_and_save_model(X, y)

# Predict intent for Task 1 (single argument)
def predict_intent(conversation):
    vectorizer, intent_classifier = load_model()
    conversation_preprocessed = preprocess(conversation)
    X_input = vectorizer.transform([conversation_preprocessed])
    return intent_classifier.predict(X_input)[0]

# Predict intent with provided model (Task 2 version)
def predict_intent_with_model(conversation, vectorizer, intent_classifier):
    conversation_preprocessed = preprocess(conversation)
    X_input = vectorizer.transform([conversation_preprocessed])
    return intent_classifier.predict(X_input)[0]

# Extract named entities and locations using BERT NER
def extract_entities_with_bert(query):
    entities = ner_model(query)
    locations = []
    current_word = ""

    for entity in entities:
        if entity['entity'] in ['I-LOC', 'B-LOC']:
            word = entity['word'].replace('##', '')
            if entity['word'].startswith('##'):
                current_word += word
            else:
                if current_word:
                    locations.append(current_word.capitalize())
                current_word = word
    if current_word:
        locations.append(current_word.capitalize())

    return entities, locations

# Count words in a text
def word_count(text):
    return len(text.split())

# Clean up entities
def clean_entities(entities):
    cleaned_entities = []
    buffer = ""

    for entity in entities:
        cleaned_word = entity['word'].replace('##', '')
        cleaned_word = re.sub(r'\W+', '', cleaned_word)
        if buffer and entity['word'].startswith('##'):
            buffer += cleaned_word
        else:
            if buffer:
                cleaned_entities.append(buffer.capitalize())
            buffer = cleaned_word
    if buffer:
        cleaned_entities.append(buffer.capitalize())

    return cleaned_entities
import sqlite3
import os
import pandas as pd

# Paths to the uploaded CSV files
car_rental_file = 'synthetic_car_rental_data.csv'
flight_file = 'synthetic_flight_data.csv'
hotel_file = 'synthetic_hotel_data.csv'
advisory_file = 'synthetic_travel_advisories.csv'

# Function to create a connection to the SQLite database
def create_connection(db_file='travel_chatbot.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

# Function to create tables for the datasets (dropping existing ones to avoid conflicts)
def create_tables(conn):
    drop_tables = """
    DROP TABLE IF EXISTS car_rental;
    DROP TABLE IF EXISTS flight;
    DROP TABLE IF EXISTS hotel;
    DROP TABLE IF EXISTS travel_advisory;
    """
    
    create_car_rental_table = """
    CREATE TABLE IF NOT EXISTS car_rental (
        Car_Rental_Company TEXT,
        City TEXT,
        Pickup_Date TEXT,
        Car_Type TEXT,
        Price_Per_Day REAL,
        Availability_Status TEXT,
        Additional_Info TEXT,
        Return_Date TEXT,
        Total_Days INTEGER
    );
    """
    
    create_flight_table = """
    CREATE TABLE IF NOT EXISTS flight (
        Airline TEXT,
        Date_of_Journey TEXT,
        Source TEXT,
        Destination TEXT,
        Dep_Time TEXT,
        Duration TEXT,
        Total_Stops TEXT,
        Additional_Info TEXT,
        Price REAL,
        Arrival_Time TEXT
    );
    """
    
    create_hotel_table = """
    CREATE TABLE IF NOT EXISTS hotel (
        Hotel_Name TEXT,
        City TEXT,
        Check_In_Date TEXT,
        Room_Type TEXT,
        Price_Per_Night REAL,
        Availability_Status TEXT,
        Additional_Info TEXT,
        Check_Out_Date TEXT,
        Total_Nights INTEGER
    );
    """
    
    create_advisory_table = """
    CREATE TABLE IF NOT EXISTS travel_advisory (
        City TEXT,
        Advisory_Date TEXT,
        Advisory_Level TEXT,
        Reason TEXT,
        Affected_Routes TEXT,
        Additional_Info TEXT,
        Validity TEXT
    );
    """
    
    try:
        c = conn.cursor()
        # Drop existing tables to avoid conflicts
        c.executescript(drop_tables)
        
        # Create fresh tables
        c.execute(create_car_rental_table)
        c.execute(create_flight_table)
        c.execute(create_hotel_table)
        c.execute(create_advisory_table)
        conn.commit()
        print("Tables created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

# Function to insert data from CSV files into their respective tables
def insert_data_from_csv(conn):
    try:
        # Load CSV files
        car_rental_data = pd.read_csv(car_rental_file)
        flight_data = pd.read_csv(flight_file)
        hotel_data = pd.read_csv(hotel_file)
        travel_advisories_data = pd.read_csv(advisory_file)

        # Insert data into respective tables
        car_rental_data.to_sql('car_rental', conn, if_exists='replace', index=False)
        flight_data.to_sql('flight', conn, if_exists='replace', index=False)
        hotel_data.to_sql('hotel', conn, if_exists='replace', index=False)
        travel_advisories_data.to_sql('travel_advisory', conn, if_exists='replace', index=False)

        conn.commit()
        print("Data inserted successfully!")
        
    except pd.errors.EmptyDataError:
        print("CSV file is empty. Please check the file content.")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except sqlite3.Error as e:
        print(f"Error inserting data into database: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Initialize the database with tables and data if it doesn't exist
def init_db(db_file='travel_chatbot.db'):
    if not os.path.exists(db_file):  # Check if the database file already exists
        print("Database does not exist. Initializing the database.")
        conn = create_connection(db_file)
        if conn is not None:
            create_tables(conn)
            insert_data_from_csv(conn)
            print("Database initialized and datasets stored.")
        else:
            print("Error! Cannot create the database connection.")
    else:
        print("Database already exists. Dropping and recreating tables.")
        conn = create_connection(db_file)
        create_tables(conn)
        insert_data_from_csv(conn)

# Run the initialization
if __name__ == "__main__":
    init_db()

    
# Predefined entity types based on dataset values
car_rental_companies = ['Hertz', 'ZoomCar', 'Carzonrent', 'Drivezy', 'Avis']
car_types = ['Convertible', 'SUV', 'Luxury', 'Sedan', 'Hatchback']
cities = ['Hyderabad', 'Bangalore', 'Mumbai', 'Pune', 'Delhi', 'Chennai', 'Jaipur', 'Kolkata', 'Goa']
availability_status = ['Booked', 'Available', 'Fully Booked']
flight_sources = ['Jaipur', 'Chennai', 'Delhi', 'Mumbai', 'Kolkata']
flight_destinations = ['Chennai', 'Pune', 'Bangalore', 'Mumbai', 'Kolkata']

airlines = ['Air India', 'IndiGo', 'SpiceJet', 'Vistara']
hotel_names = ['Ocean View', 'City Inn', 'Mountain Lodge', 'Hilltop']
room_types = ['Deluxe', 'Double', 'Single', 'Suite']
advisory_levels = ['Low', 'Severe', 'High', 'Moderate']
advisory_reasons = ['Political unrest', 'Weather', 'Security concerns', 'Health advisory']

# Additional classifications for price, duration, etc.
price_keywords = ['price', 'cost', 'rate']
duration_keywords = ['duration', 'time']
pickup_date_keywords = ['pickup date', 'return date']
check_in_out_keywords = ['check-in', 'check-out']
total_days_nights_keywords = ['total days', 'total nights']
advisory_keywords = ['advisory', 'affected routes', 'validity']

# Function to classify entities based on dataset columns and predefined types
def classify_entities(entities, locations):
    entity_classification = []
    
    # Assume entities could belong to any dataset or predefined list
    for entity in entities:
        if isinstance(entity, str):  # Ensure entity is a string before applying .lower()
            entity_lower = entity.lower()

            # Car Rental dataset classifications
            if entity_lower in [c.lower() for c in car_rental_companies]:
                entity_classification.append(f"Car Rental Company: {entity.capitalize()}")
            elif entity_lower in [c.lower() for c in car_types]:
                entity_classification.append(f"Car Type: {entity.capitalize()}")
            elif entity_lower in availability_status:
                entity_classification.append(f"Availability Status: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in pickup_date_keywords):
                entity_classification.append(f"Pickup/Return Date: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in price_keywords):
                entity_classification.append(f"Price Per Day: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in total_days_nights_keywords):
                entity_classification.append(f"Total Days: {entity.capitalize()}")
            
            # Flight dataset classifications
            elif entity_lower in [a.lower() for a in airlines]:
                entity_classification.append(f"Airline: {entity.capitalize()}")
            elif entity_lower in [s.lower() for s in flight_sources]:
                entity_classification.append(f"Flight Source: {entity.capitalize()}")
            elif entity_lower in [d.lower() for d in flight_destinations]:
                entity_classification.append(f"Flight Destination: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in price_keywords):
                entity_classification.append(f"Price: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in duration_keywords):
                entity_classification.append(f"Duration: {entity.capitalize()}")
            elif 'total stops' in entity_lower:
                entity_classification.append(f"Total Stops: {entity.capitalize()}")
            
            # Hotel dataset classifications
            elif entity_lower in [h.lower() for h in hotel_names]:
                entity_classification.append(f"Hotel Name: {entity.capitalize()}")
            elif entity_lower in [r.lower() for r in room_types]:
                entity_classification.append(f"Room Type: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in check_in_out_keywords):
                entity_classification.append(f"Check-In/Check-Out Date: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in price_keywords):
                entity_classification.append(f"Price Per Night: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in total_days_nights_keywords):
                entity_classification.append(f"Total Nights: {entity.capitalize()}")
            
            # Travel advisory classifications
            elif entity_lower in [al.lower() for al in advisory_levels]:
                entity_classification.append(f"Advisory Level: {entity.capitalize()}")
            elif entity_lower in [ar.lower() for ar in advisory_reasons]:
                entity_classification.append(f"Advisory Reason: {entity.capitalize()}")
            elif any(keyword in entity_lower for keyword in advisory_keywords):
                entity_classification.append(f"Advisory Details: {entity.capitalize()}")
    
    # Add the identified locations as cities
    for location in locations:
        if location in cities:
            entity_classification.append(f"City: {location.capitalize()}")
    
    return ', '.join(entity_classification)
import requests

import os


# Function to get the Amadeus API token
def get_amadeus_token():
    client_id = st.secrets["AMADEUS_CLIENT_ID"]
    client_secret = st.secrets["AMADEUS_CLIENT_SECRET"]    
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(auth_url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Function to get flight offers from Amadeus API
def get_flight_offers(origin, destination, departure_date, return_date=None):
    access_token = get_amadeus_token()
    
    if "error" in access_token:
        return {"error": access_token["error"]}
    
    api_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": 1,
        "travelClass": "ECONOMY",
        "max": 10
    }
    
    if return_date:
        params["returnDate"] = return_date
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
import requests

# IATA Codes for Cities (for Flights and Hotels)
city_iata_mapping = {
    "Mumbai": "BOM",
    "Delhi": "DEL",
    "Bangalore": "BLR",
    "Hyderabad": "HYD",
    "Chennai": "MAA",
    "Kolkata": "CCU",
    "Pune": "PNQ",
    "Jaipur": "JAI"
}

# Function to get a list of hotels in a city using Amadeus API (Using IATA code)
def get_hotel_list_by_city(city):
    """
    Fetches a list of hotels by city IATA code from the Amadeus API.
    """
    city_code = city_iata_mapping.get(city)
    if not city_code:
        return {"error": "Invalid city selection. Please select a valid city."}
    
    access_token = get_amadeus_token()
    if "error" in access_token:
        return {"error": access_token["error"]}
    
    api_url = f"https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "cityCode": city_code
    }
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

import requests

# Function to get hotel details by hotelId (using Amadeus API)
def get_hotel_details_by_id(hotel_id):
    """
    Fetches detailed hotel information using hotelId from the Amadeus API.
    """
    access_token = get_amadeus_token()
    
    if "error" in access_token:
        return {"error": access_token["error"]}
    
    api_url = f"https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-hotels?hotelIds={hotel_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX errors
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}






import requests

# Mapping of locationId to City
location_id_to_city = {
    10: "Mumbai",
    11: "Delhi",
    12: "Bangalore",
    13: "Hyderabad",
    14: "Chennai",
    15: "Kolkata",
    16: "Pune",
    17: "Jaipur",
    18: "Goa",
    19: "Ahmedabad",
    20: "Surat",
    21: "Lucknow",
    22: "Kanpur",
    23: "Varanasi",
    24: "Agra",
    25: "Shimla",
    26: "Manali",
}

# Function to map locationId to City
def get_city_by_location_id(location_id):
    """Maps a given locationId to a city name."""
    return location_id_to_city.get(location_id, "Unknown Location")

# Function to get vehicle details (number, price, etc.) by carId
def get_vehicle_details_by_car_id(car_id):
    """
    Fetches detailed vehicle information using carId from the ZoomCar API.
    """
    api_url = f"https://freeapi.miniprojectideas.com/api/ZoomCar/GetCarById?id={car_id}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise exception for 4XX/5XX errors
        vehicle_data = response.json()  # Get the JSON response
        if "data" in vehicle_data:
            return vehicle_data["data"]  # Return the 'data' part
        else:
            return {"error": "Unexpected response format."}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Function to get car rentals by city from the ZoomCar API
def get_car_rentals(city, pickup_date=None, dropoff_date=None):
    """
    Fetches car rental data from the ZoomCar API using the city as the query.
    Maps locationId to the actual city names for display purposes and then fetches vehicle details.
    """
    api_url = f"https://freeapi.miniprojectideas.com/api/ZoomCar/searchCarByLocation?query={city}"

    try:
        # Send GET request to the API
        response = requests.get(api_url)
        response.raise_for_status()  # Raise exception for 4XX/5XX errors
        car_data = response.json()  # Get the JSON response
    except requests.exceptions.RequestException as e:
        # Return an error in case of an exception
        return {"error": str(e)}

    # Process and map locationId to city for each car in the result
    if car_data and car_data.get("result") and car_data.get("data"):
        for car in car_data["data"]:
            # Replace the locationId with the actual city name for display purposes
            car["mappedLocation"] = get_city_by_location_id(car.get("locationId", 0))
            
            # Fetch detailed vehicle information using carId
            vehicle_details = get_vehicle_details_by_car_id(car.get("carId"))
            
            # If vehicle details were fetched successfully, add them to the car data
            if vehicle_details and vehicle_details.get("carId"):
                car["vehicleNumber"] = vehicle_details.get("vehicleNo", "N/A")
                car["finalPrice"] = vehicle_details.get("pricing", "N/A")
            else:
                car["vehicleNumber"] = "N/A"
                car["finalPrice"] = "N/A"
    
    return car_data


mock_db = {
    'flight': [],
    'hotel': [],
    'car': []
}

# Mock function to store bookings in the database
def mock_booking_in_db(service_type, *booking_details):
    mock_db[service_type].append({
        "service": service_type,
        "details": booking_details
    })

# Mock function to fetch bookings from the database
def fetch_booking_from_db(service_type):
    return mock_db[service_type]

# Mock function to cancel bookings in the database
def cancel_booking_in_db(service_type, booking_to_cancel):
    mock_db[service_type].remove(booking_to_cancel)

from utils import get_amadeus_token

import requests
import os


def get_iata_code(city_name):
    # Manually map city names to IATA codes or use an API lookup
    iata_lookup = {
        'Delhi': 'DEL',
        'Mumbai': 'BOM',
        'Bangalore': 'BLR',
        'Jaipur': 'JAI',
        # Add more cities and IATA codes as needed
    }
    
    return iata_lookup.get(city_name, None)



# Fetch recommendations from Amadeus API
def fetch_amadeus_recommendations(city_code, traveler_country_code, destination_country_code=None):
    token = get_amadeus_token()
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Construct the URL for the API request
    url = f"https://test.api.amadeus.com/v1/reference-data/recommended-locations?cityCodes={city_code}&travelerCountryCode={traveler_country_code}"
    
    # Add destination country code if available
    if destination_country_code:
        url += f"&destinationCountryCodes={destination_country_code}"
    
    print(f"Requesting URL: {url}")  # Debugging: print the full request URL
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Amadeus recommendations: {e}")
        return None
    


import requests
from utils import get_amadeus_token  # Assuming you have this function defined as shown earlier

# Function to fetch flight delay and gate change information
def get_flight_updates(airport_code, travel_date):
    token = get_amadeus_token()  # Assuming the function exists
    if not token:
        return 0, 0, [], []

    # Modify your API call to include the travel date
    url = f'https://api.amadeus.com/v1/airport/predictions/on-time?airportCode={airport_code}&date={travel_date}&apikey={token}'
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        flight_data = response.json()
        delayed_flights = []
        gate_changes = []

        for flight in flight_data.get('flights', []):
            if flight.get('delay') or flight.get('gateChange'):
                delayed_flights.append(flight)

                if flight.get('gateChange'):
                    gate_changes.append(flight)

        return len(delayed_flights), len(gate_changes), delayed_flights, gate_changes
    else:
        return 0, 0, [], []


# Function to provide customer support information
def get_customer_support():
    support_info = {
        "email": "support@travelchat.com",
        "phone": "+1-800-555-1234",
        "live_chat": "https://travelchat.com/support",
        "faq": "https://travelchat.com/faq"
    }
    return support_info
