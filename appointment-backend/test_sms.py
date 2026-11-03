from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

print("SID:", os.getenv("TWILIO_SID"))
print("AUTH:", os.getenv("TWILIO_AUTH"))
print("NUMBER:", os.getenv("TWILIO_NUMBER"))

account_sid = os.getenv("TWILIO_SID")
auth_token = os.getenv("TWILIO_AUTH")
twilio_number = os.getenv("TWILIO_NUMBER")

client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Hello ",
    from_=twilio_number,
    to="+15103645765"
)

print("Message SID:", message.sid)
print("Message Body:", message.body)
