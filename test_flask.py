from flask import Flask, request
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        return f"Action: {action}"
    return '''
        <form method="POST">
            <input type="text" name="nick" required>
            <button type="submit" name="action" value="save">Save</button>
            <button type="submit" name="action" value="ban" formnovalidate>Ban</button>
        </form>
    '''

if __name__ == "__main__":
    app.run(port=5000)
