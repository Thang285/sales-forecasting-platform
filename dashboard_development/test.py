import streamlit_authenticator as stauth

hashed_pw = stauth.Hasher().hash("12345678")

print("Your hash password is: ",hashed_pw)
