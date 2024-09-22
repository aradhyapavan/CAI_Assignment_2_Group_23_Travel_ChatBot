

---

# ✈️ TravelChat: Real-Time Travel Booking & Assistance 🧳

**TravelChat** is a real-time travel booking and assistance application designed to streamline travel planning. It provides users with flight bookings, hotel reservations, car rentals, and real-time travel alerts, along with personalized travel suggestions based on user preferences and history.

---

## 🛠️ Application Structure

### 1. **`app.py`**
- Entry point for the Streamlit interface that manages:
  - **Flight Booking**: Real-time flight data fetched from the Amadeus API.
  - **Hotel Booking**: Allows users to select hotels based on location and availability.
  - **Car Rental**: Retrieves car rental options from the ZoomCar API.
  - **Travel History**: Displays the user's travel history, allowing them to view and cancel bookings.
  - **Real-Time Flight Updates**: Shows real-time updates for flight delays, gate changes, and cancellations.

### 2. **`utils.py`**
This module handles core operations, such as API interactions and database queries:
- **Amadeus & ZoomCar APIs**:
  - `get_flight_offers()`: Retrieves real-time flight offers, including prices, airlines, and travel classes.
  - `get_hotel_list_by_city()`: Fetches available hotels in a specific city based on user-inputted dates.
  - `get_car_rentals()`: Retrieves available rental cars in the user-selected city.
  - `get_flight_updates()`: Provides real-time flight delay and gate change information using the Amadeus API.
- **Database Management**:
  - `store_booking()`: Stores flight, hotel, and car rental bookings in an SQLite database.
  - `fetch_booking_history()`: Retrieves past bookings (both active and canceled).
  - `cache_api_data()`: Caches API responses to minimize repeated API requests.

### 3. **`login_signup.py`**
Handles user authentication, including:
- **Sign Up** for new users.
- **Log In** for existing users.
- **Session Management**: Uses Streamlit session state to keep track of logged-in users.

### 4. **SQLite Database (`travel_booking.db`)**
The SQLite database is responsible for:
- **User Bookings**: Stores all user bookings and interactions (flights, hotels, cars).
- **API Data Caching**: Reduces redundant API calls by caching API responses.
- **Booking History**: Manages booking statuses (active/canceled) and supports cancellation within 24 hours.

### 5. **Synthetic Datasets**
These datasets simulate real-world travel data for training and testing:
- **`synthetic_flight_data.csv`**: A dataset containing sample flight data for testing purposes.
- **`synthetic_hotel_data.csv`**: Includes hotel details, such as room types, prices, and availability.
- **`synthetic_car_rental_data.csv`**: Simulates car rental options, including vehicle types, availability, and pricing.

---

## 📝 Task Breakdown

### **Task 1: Natural Language Processing for Travel Queries**
- **Intent Classification**: Classifies user requests such as flight booking, hotel inquiry, or car rentals.
- **Entity Extraction**: Using `spaCy`, extracts key entities like city names, travel dates, and airlines.
- **Date Parsing**: Leverages `DateParser` to convert natural language dates (e.g., "next Friday") into exact dates.

### **Task 2: Dataset Preprocessing and Model Training**
- **Synthetic Dataset**: A synthetic dataset of travel-related queries is preprocessed for training.
- **Model Training**: The dataset is used to fine-tune the classification models for improved accuracy.

### **Task 3: Travel Database Querying and Integration**
- **Real-Time API Integration**: Connects to external APIs (Amadeus for flights and hotels, ZoomCar for car rentals) to retrieve real-time travel data.
- **Database Interaction**: Stores and retrieves data from an SQLite database for efficient querying and data persistence.

### **Task 4: API Integration for Travel Services**
- **Flight Booking**: Integrates the Amadeus API to fetch real-time flight options, including prices, airlines, and travel classes.
- **Hotel Booking**: Retrieves real-time hotel availability and room details based on user inputs.
- **Car Rentals**: Integrates the ZoomCar API to fetch real-time car rental options.

### **Task 5: Personalized Travel Suggestions**
- **Travel Recommendations**: Uses the user’s history and preferences to recommend flights, hotels, and cars.
- **Query Matching**: Matches previous user queries with current inputs to provide personalized suggestions.

### **Task 6: Booking and Cancellation Management**
- **Booking Handling**: Allows users to confirm bookings for flights, hotels, and car rentals, storing the booking details in the SQLite database.
- **Cancellations**: Users can cancel bookings within 24 hours via the travel history interface.

### **Task 7: Real-Time Travel Alerts and Customer Support**
- **Flight Updates**: Fetches real-time flight updates, including delays and gate changes, using the Amadeus API.
- **Customer Support**: Provides multiple channels for customer support, including email, live chat, and an FAQ section.

---

## 💻 Technical Overview

### **Natural Language Processing (NLP)**:
- **Intent Classification**: The system classifies user intents (e.g., booking a flight or renting a car) using pre-trained models.
- **Entity Recognition**: `spaCy` is used to extract relevant entities (e.g., city names, dates, airlines) from user input.
- **Date Parsing**: `DateParser` converts natural language dates (like "next Tuesday") into a structured format that the system can use.

### **API Integrations**:
- **Amadeus API**: Provides real-time data for flights and hotels, including prices, airlines, room availability, and more.
- **ZoomCar API**: Fetches car rental availability, prices, and vehicle details.
- **Caching with SQLite**: Minimizes redundant API calls by caching API responses and storing them in an SQLite database.

### **User Interface (UI)**:
- **Streamlit**: Provides an interactive user interface that allows users to book flights, hotels, and cars, view travel history, and receive personalized suggestions.

### **Data Management**:
- **SQLite Database**: Stores user bookings and caches API responses, ensuring persistence and faster querying.
- **Preprocessing**: The synthetic datasets are preprocessed to train the models for entity extraction and intent classification.

---

## 🔧 Getting Started

### Prerequisites:
- **Python 3.8+**: Make sure you have Python installed on your system.
- **Virtual Environment** (Optional): Helps manage dependencies and avoid conflicts.

### Installation:

1. Clone the repository:
    ```bash
    git clone https://github.com/aradhyapavan/CAI_Assignment_2_Group_23_Travel_ChatBot.git
    cd TravelChat
    ```

2. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Setup API Keys:
Create a `.env` file in the root directory and add the following API credentials:
```bash
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
ZOOMCAR_API_KEY=your_zoomcar_api_key
```

### Running the Application:
1. Launch the Streamlit application:
    ```bash
    streamlit run app.py
    ```

2. Access the app by opening your browser and navigating to `http://localhost:8501`.

---

## 🎯 Conclusion

**TravelChat** offers a complete solution for managing your travel bookings, from flights to hotels to car rentals. It provides real-time booking data, personalized suggestions, and a user-friendly interface to simplify travel planning. The integration with APIs like Amadeus and ZoomCar ensures that users receive up-to-date information, while the system's booking history and cancellation features provide flexibility and control.

Explore the project on [GitHub](https://github.com/aradhyapavan/CAI_Assignment_2_Group_23_Travel_ChatBot/) and streamline your travel experience today!

---

