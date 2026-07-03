import logging
from flask import Flask, request, Response, abort
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import os
from dotenv import load_dotenv

PUBLIC_URL = "https://zenzic.xyz/sms-webhook"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sms-webhook")

load_dotenv() 
app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
)

validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_AUTH_TOKEN"])

def validate_twilio_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get("X-Twilio-Signature", "")
        params = request.form.to_dict()

        if not signature:
            abort(403)

        if not validator.validate(PUBLIC_URL, params, signature):
            abort(403)

        return f(*args, **kwargs)
    return decorated

@app.route("/sms-webhook", methods=["POST"])
@validate_twilio_request
def sms_webhook():
    from_number = request.form.get("From")
    body = request.form.get("Body")

    try:
        client.messages.create(
            from_=os.environ["TWILIO_NUMBER"],
            to=os.environ["MY_PHONE_NUMBER"],
            body=f"New reply from {from_number}: {body}"
        )
        logger.info(f"Forwarded message from {from_number} to {os.environ['MY_PHONE_NUMBER']}")
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")

    return Response('<Response></Response>', mimetype='text/xml')

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)