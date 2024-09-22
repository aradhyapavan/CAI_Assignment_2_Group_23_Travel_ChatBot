import streamlit as st
from utils import get_flight_offers, get_hotel_list_by_city, get_car_rentals,get_vehicle_details_by_car_id,get_hotel_details_by_id
from datetime import datetime, timedelta
import time



import login_signup  # Assuming login_signup is your module for handling login and signup

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

# IATA Codes for Cities (for Flights) and City Names (for Car Rentals)
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

# Location Mapping for Car Rentals
location_id_mapping = {
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
    27: "Mysore",
    28: "Bhopal",
    29: "Indore"
}

# Airline code to airline full name mapping
airline_code_mapping = {
    "AI": "Air India",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "UK": "Vistara"
}


# Main Greeting and API Information
st.title("🤖 Welcome to Travel Services!")
if 'user_name' in st.session_state:
    st.markdown(f"Hello, {st.session_state['user_name']}! I'm here to assist you with your travel needs.")
else:
    st.markdown("Hello! I'm here to assist you with your travel needs.")

st.markdown("### 🌐 APIs Used:")
st.markdown("""
- **Flight Offers API**: Fetches the latest flight offers based on your selected routes and dates.  
  **URL**: [Flight Offers API](https://api.example.com/flight-offers)

- **Hotel List API**: Retrieves a list of hotels in your chosen city, including detailed information and availability.  
  **URL**: [Hotel List API](https://api.example.com/hotel-list)

- **Car Rentals API**: Provides car rental options in your selected city, complete with pricing and vehicle details.  
  **URL**: [Car Rentals API](https://api.example.com/car-rentals)
""")



# Function to format duration from ISO8601 to human-readable format
def format_duration(duration_iso):
    import isodate
    duration = isodate.parse_duration(duration_iso)
    hours = duration.total_seconds() // 3600
    minutes = (duration.total_seconds() % 3600) // 60
    return f"{int(hours)}h {int(minutes)}m"

# Convert price to INR (Assuming 1 EUR = 110 INR for demonstration purposes)
def convert_to_inr(eur_price):
    conversion_rate = 110  # Example conversion rate
    inr_price = float(eur_price) * conversion_rate
    return f"{inr_price:.2f} INR"

# Function to calculate the layover duration
def calculate_layover(arrival_time, departure_time):
    arrival_dt = datetime.fromisoformat(arrival_time)
    departure_dt = datetime.fromisoformat(departure_time)
    layover_duration = departure_dt - arrival_dt
    hours, remainder = divmod(layover_duration.total_seconds(), 3600)
    minutes = remainder // 60
    return f"{int(hours)}h {int(minutes)}m"

# Function to format time from ISO 8601 format to a readable time format (HH:MM)
def format_time(time_iso):
    dt = datetime.fromisoformat(time_iso)
    return dt.strftime('%H:%M')

# Function to convert IATA codes back to city names
def get_city_name(iata_code):
    for city, iata in city_iata_mapping.items():
        if iata == iata_code:
            return city
    return iata_code  # Return IATA code if no match found

# Add Bootstrap 5 CDN for styling
bootstrap_cdn = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
"""
st.markdown(bootstrap_cdn, unsafe_allow_html=True)



# Add a proper greeting and header for the task
st.title("Task 4: Travel Services - Flight, Hotel, and Car Rental Search")



# Service Selection
service_choice = st.selectbox("Which service do you want?", ["Flight Booking", "Hotel List", "Car Rental"])

# Hotel List by City
if service_choice == "Hotel List":
    st.header("Hotel List by City")
    city = st.selectbox("Select City", ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata"])
    
    if st.button("Search Hotels by City"):
        with st.spinner("Fetching hotel data... Please wait a moment."):
            time.sleep(1)  # Simulate delay for API fetching
            hotel_list_data = get_hotel_list_by_city(city)
        
        if "error" in hotel_list_data:
            st.error(hotel_list_data['error'])
        else:
            if "data" in hotel_list_data:
                hotels = hotel_list_data["data"][:10]  # Limiting to 10 results
                for hotel in hotels:
                    hotel_name = hotel.get("name", "N/A")
                    address = hotel.get("address", {}).get("countryCode", "N/A")
                    hotel_id = hotel.get("hotelId", "N/A")

                    # Display the hotel information (without sentiments)
                    hotel_html = f"""
                    <div class="card mb-3 text-light bg-dark border" style="max-width: 540px;">
                        <div class="card-body">
                            <h5 class="card-title">{hotel_name}</h5>
                            <p class="card-text"><strong>Address:</strong> {address}</p>
                            <p class="card-text"><strong>Hotel ID:</strong> {hotel_id}</p>
                        </div>
                    </div>
                    """
                    
                    st.markdown(hotel_html, unsafe_allow_html=True)




# Flight Booking
elif service_choice == "Flight Booking":
    st.header("Flight Booking")
    
    # City Selection for Source and Destination
    source_city = st.selectbox("Select Source City", list(city_iata_mapping.keys()))
    destination_city = st.selectbox("Select Destination City", list(city_iata_mapping.keys()))
    
    # Validate that source and destination are not the same
    if source_city == destination_city:
        st.error("Source and Destination cannot be the same.")
    else:
        # Date input for future dates only
        departure_date = st.date_input("Departure Date:", min_value=datetime.now().date())
        return_date = st.date_input("Return Date (optional):", min_value=departure_date)
        
        # Check if return date is optional or after departure date
        if return_date and return_date < departure_date:
            st.error("Return date cannot be before departure date.")
        else:
            if st.button("Search Flights"):
                # Display a loading message and spinner
                with st.spinner("Fetching flight data... This may take a few seconds."):
                    time.sleep(1)  # Simulate a delay for API fetching

                    # Get IATA codes for selected cities
                    origin = city_iata_mapping[source_city]
                    destination = city_iata_mapping[destination_city]
        
                    # Fetch flight offers using API
                    flight_data = get_flight_offers(
                        origin,
                        destination,
                        departure_date.strftime('%Y-%m-%d'),
                        return_date.strftime('%Y-%m-%d') if return_date else None
                    )
        
                if "error" in flight_data:
                    st.error(flight_data['error'])
                else:
                    if "data" in flight_data:
                        offers = flight_data["data"][:10]
                        for offer in offers:
                            airline_code = offer["validatingAirlineCodes"][0]
                            price = offer["price"]["total"]
                            inr_price = convert_to_inr(price)
                            itineraries = offer['itineraries']
                            
                            # Get the full airline name using the mapping
                            airline_name = airline_code_mapping.get(airline_code, airline_code)
                            
                            for itinerary in itineraries:
                                departure = get_city_name(itinerary["segments"][0]["departure"]["iataCode"])
                                arrival = get_city_name(itinerary["segments"][-1]["arrival"]["iataCode"])
                                duration_iso = itinerary["duration"]
                                duration = format_duration(duration_iso)
    
                                # Number of stops and layover information
                                num_stops = len(itinerary["segments"]) - 1
                                layover_info = []
                                
                                if num_stops > 0:
                                    for i in range(len(itinerary["segments"]) - 1):
                                        layover_airport = get_city_name(itinerary["segments"][i]["arrival"]["iataCode"])
                                        layover_duration = calculate_layover(itinerary["segments"][i]["arrival"]["at"], itinerary["segments"][i + 1]["departure"]["at"])
                                        layover_info.append(f"Layover at {layover_airport} for {layover_duration}")
    
                                # Extract available classes
                                available_classes = set()
                                for segment in itinerary["segments"]:
                                    cabin = segment.get("cabin")
                                    if cabin:
                                        available_classes.add(cabin)
                                    
                                    # Get departure and arrival times
                                    departure_time = format_time(segment["departure"]["at"])
                                    arrival_time = format_time(segment["arrival"]["at"])
                                    
                                    # Display segment details
                                    st.write(f"Segment: {get_city_name(segment['departure']['iataCode'])} to {get_city_name(segment['arrival']['iataCode'])}")
                                    st.write(f"Departure: {departure_time}, Arrival: {arrival_time}")
    
                                # Display flight details
                                flight_html = f"""
                                <div class="card my-3 text-light bg-dark border" style="max-width: 540px;">
                                    <div class="card-body">
                                        <h5 class="card-title">{airline_name} ({airline_code})</h5>
                                        <p class="card-text"><strong>Price:</strong> {inr_price}</p>
                                        <p class="card-text"><strong>Duration:</strong> {duration}</p>
                                        {"<p class='card-text'><strong>Stops:</strong> " + str(num_stops) + " stop(s)</p>" if num_stops > 0 else "<p class='card-text'><strong>Non-stop flight</strong></p>"}
                                        <p class="card-text"><strong>Available Classes:</strong> {', '.join(available_classes) if available_classes else 'Unavailable'}</p>
                                    </div>
                                </div>
                                """
                                st.markdown(flight_html, unsafe_allow_html=True)

# Car Rental
# Car Rental
elif service_choice == "Car Rental":
    st.header("Car Rental")
    
    # Dropdown for selecting city
    city = st.selectbox("Select City for Car Rental", list(city_iata_mapping.keys()))
    
    if st.button("Search Car Rentals"):
        with st.spinner("Fetching car rental data... Please wait a moment."):
            time.sleep(1)  # Simulate delay for API fetching
            car_data = get_car_rentals(city, None, None)
        
        if "error" in car_data:
            st.error(car_data['error'])
        else:
            if "data" in car_data:
                cars = car_data["data"][:15]  # Limit to 25 results
                for car in cars:
                    car_model = car.get("name", "N/A")
                    car_brand = car.get("brand", "N/A")
                    car_image = car.get("imageUrl", "https://via.placeholder.com/80x80")  # Default image if not available
                    price_description = car.get("pricingDescription", "Price details not available")
                    location = car.get("mappedLocation", "Unknown Location")
                    vehicle_number = car.get("vehicleNumber", "N/A")
                    final_price = car.get("finalPrice", "N/A")
                    accessories = [acc["accessoriesTitle"] for acc in car.get("carAccessoriess", [])]

                    # HTML layout for car rental display using Bootstrap 5
                    car_html = f"""
                    <div class="card mb-3 text-light bg-dark border" style="max-width: 540px;">
                        <div class="row g-0">
                            <div class="col-md-4">
                                <img src="{car_image}" class="img-fluid rounded-start" alt="{car_model}">
                            </div>
                            <div class="col-md-8">
                                <div class="card-body">
                                    <h5 class="card-title">{car_brand} - {car_model}</h5>
                                    <p class="card-text"><strong>Location:</strong> {location}</p>
                                    <p class="card-text"><strong>Pricing:</strong> {price_description}</p>
                                    <p class="card-text"><strong> Price Per Day:</strong> {final_price}</p>
                                    <p class="card-text"><strong>Vehicle Number:</strong> {vehicle_number}</p>
                                    <p class="card-text"><strong>Accessories:</strong> {', '.join(accessories) if accessories else 'None'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(car_html, unsafe_allow_html=True)
                  
