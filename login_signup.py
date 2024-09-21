# This must be the very first Streamlit command in the script.
import streamlit as st
st.set_page_config(page_title="Travel Assistant Chatbot", page_icon="✈️", layout="centered")

import sqlite3

# Modified database connection setup
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn

# Use this function to get a connection and cursor whenever needed
def user_exists(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    c.close()
    conn.close()
    return user

def add_user(name, email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    c.close()
    conn.close()

# Layout for the login/signup page
def login_signup_layout():
    st.title("🛫 Travel Assistant Chatbot")
    st.markdown("""
        Welcome to the Travel Assistant Chatbot. 
        Please login or sign up to start planning your trip.
    """)

    col1, col2 = st.columns(2)
    
    with col1:
        login()
        
    with col2:
        signup()

# Login function
def login():
    st.subheader("Login")
    email = st.text_input("Enter your email", key="login_email")
    if st.button("Log In"):
        user = user_exists(email)
        if user:
            st.success(f"Welcome back, {user[0]}!")
            st.session_state['logged_in'] = True
            st.session_state['name'] = user[0]
            st.session_state['email'] = user[1]
        else:
            st.warning("No user found. Please sign up.")

# Signup function
def signup():
    st.subheader("Signup")
    name = st.text_input("Enter your name", key="signup_name")
    email = st.text_input("Enter your email", key="signup_email")
    if st.button("Sign Up"):
        if user_exists(email):
            st.warning("User already exists. Please login instead.")
        else:
            add_user(name, email)
            st.success(f"Account created for {name}. You can now log in.")
            st.session_state['logged_in'] = True
            st.session_state['name'] = name
            st.session_state['email'] = email

# Main function to show the layout
if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        st.success(f"Logged in as {st.session_state['name']}")
        # Add your main app logic here once logged in
    else:
        login_signup_layout()
