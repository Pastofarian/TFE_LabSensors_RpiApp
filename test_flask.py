from flask import Flask
app = Flask(__name__)

# Main route
@app.route("/")
def test_flask():
    # Return a response from the main route
    return "Flask test reponse"

# Try another route for "/sample"
@app.route("/sample")
def sample_route():
    # Return a response from the sample route
    return "C'est un exemple de route"

# Run the code on all network  and port 8080
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

