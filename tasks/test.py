from google import genai
import os

print("key=" + os.environ.get("NOT_OPENAPI_KEY"))
client = genai.Client(
    api_key=os.environ.get("NOT_OPENAPI_KEY"),
)
