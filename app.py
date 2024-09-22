import streamlit as st
import login_signup  # Import login and signup module
st.set_page_config(page_title="Travel Assistant Chatbot", page_icon="✈️", layout="centered")



# Check if user is logged in
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Display login/signup if not logged in
if not st.session_state['logged_in']:
    auth_option = st.sidebar.selectbox("Login or Signup", ["Login", "Signup"])
    if auth_option == "Login":
        login_signup.login()
    elif auth_option == "Signup":
        login_signup.signup()

# If logged in, show the main app
if st.session_state['logged_in']:
    # Add header with logo and group information
    st.markdown("""
    <center><img src="https://d3njjcbhbojbot.cloudfront.net/api/utilities/v1/imageproxy/http://coursera-university-assets.s3.amazonaws.com/b9/c608c79b5c498a8fa55b117fc3282f/5.-Square-logo-for-landing-page---Alpha.png?auto=format%2Ccompress&dpr=1&w=180&h=180" ></center>
    <h4><center><b>Conversational AI Assignment 2 – Problem Statement 1</b></center></h1>
    <h4><center>Subject & Code - Conversational AI (S2-23_AIMLCZG521)</center></h2>
    <h4><b>Group Number - 23</b></h4>
    <h4><b>Group Members:</b><br>
    Aradhya Pavan H S (2022ac05457)<br>
    V V R V Chaitanya (2022ac05211)<br>
    J Niharika (2022ac05559)<br>
    Tejovardhan Medamarti (2022ac05124)
    </h4>
    """, unsafe_allow_html=True)

    # Title of the app
    st.title(f"Welcome {st.session_state['name']} to the Travel Chatbot App")
   
    # Sidebar for selecting tasks
    st.sidebar.title("Tasks")
    task = st.sidebar.radio(
        "Choose a task",
        ["Task 1: Natural Language Understanding",
         "Task 2: Training on Travel-Related Conversations",
         "Task 3: Database Integration and Querying",
         "Task 4: API Handling",
         "Task 5: Personalized Travel Recommendations",
         "Task 6: Booking and Cancellation Management",
         "Task 7: Real-Time Travel Updates and Customer Support"]
    )

    # Task routing with proper descriptions
    if task == "Task 1: Natural Language Understanding":
        st.write("### Task 1: Natural Language Understanding")
        st.markdown("""
        This task focuses on understanding travel-related terminologies and extracting intent, service, locations, and dates from the user query.
        You can access Task 1 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 2: Training on Travel-Related Conversations":
        st.write("### Task 2: Training on Travel-Related Conversations")
        st.markdown("""
        Train the chatbot using the synthetic travel conversation dataset to enhance its ability to understand and respond to travel queries.
        You can access Task 2 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 3: Database Integration and Querying":
        st.write("### Task 3: Database Integration and Querying")
        st.markdown("""
        Integrate the chatbot with a travel information database to provide real-time responses. The goal is to fetch accurate flight schedules, hotel availability, and travel advisories.
        You can access Task 3 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 4: API Handling":
        st.write("### Task 4: API Handling")
        st.markdown("""
        Implement API integrations for services like flight bookings, hotel reservations, and car rentals, ensuring seamless interactions and real-time data retrieval.
        You can access Task 4 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 5: Personalized Travel Recommendations":
        st.write("### Task 5: Personalized Travel Recommendations")
        st.markdown("""
        Analyze user preferences and travel history to recommend tailored destinations, accommodations, and activities.
        You can access Task 5 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 6: Booking and Cancellation Management":
        st.write("### Task 6: Booking and Cancellation Management")
        st.markdown("""
        Enable the chatbot to manage travel bookings and cancellations, offering alternative options and handling modifications.
        You can access Task 6 from the left sidebar.
        """, unsafe_allow_html=True)

    elif task == "Task 7: Real-Time Travel Updates and Customer Support":
        st.write("### Task 7: Real-Time Travel Updates and Customer Support")
        st.markdown("""
        Provide real-time updates on travel itineraries, such as flight delays and gate changes, while also offering customer support for inquiries and troubleshooting.
        You can access Task 7 from the left sidebar.
        """, unsafe_allow_html=True)

    # Add logout button
    if st.sidebar.button("Logout"):
        login_signup.logout()

# Add some spacing at the bottom
st.markdown("<br><br><br>", unsafe_allow_html=True)
