from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home_page():
    return render_template('main.html')


@app.route('/knockouts')
def knockouts_page():
    return render_template('knockouts.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

if __name__ == "__main__":
    app.run(debug=True)