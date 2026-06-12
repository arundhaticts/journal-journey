from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk
from datetime import datetime
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# -------------------- NLTK Downloads --------------------

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('vader_lexicon')

# -------------------- Flask Setup --------------------

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# -------------------- Database Models --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    entries = db.relationship('DiaryEntry', backref='author', lazy=True)


class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    sentiment = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()

# -------------------- Forms --------------------

class LoginForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=2, max=20)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    submit = SubmitField('Login')


class SignupForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=2, max=20)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    submit = SubmitField('Sign Up')


# -------------------- NLP Setup --------------------

category_keywords = {
    "Work": [
        "work", "job", "office", "project", "task",
        "meeting", "deadline", "client", "manager", "team"
    ],
    "Health": [
        "health", "fitness", "exercise", "gym",
        "diet", "sleep", "doctor", "meditation"
    ],
    "Relationships": [
        "love", "friend", "family", "partner",
        "relationship", "parents", "siblings"
    ],
    "Personal Development": [
        "growth", "learning", "goal", "motivation",
        "discipline", "confidence", "improve"
    ],
    "Hobbies": [
        "music", "reading", "writing", "gaming",
        "travel", "photography", "drawing", "cooking"
    ]
}

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
sid = SentimentIntensityAnalyzer()


def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    tokens = [
        word for word in tokens
        if word.isalnum() and word not in stop_words
    ]
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    return tokens


def categorize_entry(text):
    words = preprocess_text(text)

    scores = {
        category: 0
        for category in category_keywords
    }

    for word in words:
        for category, keywords in category_keywords.items():
            if word in keywords:
                scores[category] += 1

    if max(scores.values()) == 0:
        return "Personal Development"

    return max(scores, key=scores.get)


def analyze_sentiment(text):
    sentiment_scores = sid.polarity_scores(text)

    if sentiment_scores['compound'] >= 0.05:
        sentiment = "Positive"
    elif sentiment_scores['compound'] <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return sentiment


# -------------------- Routes --------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if 'user_id' in session:
        return redirect(url_for('index'))

    form = SignupForm()

    if form.validate_on_submit():

        existing_user = User.query.filter_by(
            username=form.username.data
        ).first()

        if existing_user:
            flash("Username already exists!", "danger")
            return redirect(url_for('signup'))

        hashed_password = bcrypt.generate_password_hash(
            form.password.data
        ).decode('utf-8')

        user = User(
            username=form.username.data,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully!", "success")
        return redirect(url_for('login'))

    return render_template(
        'signup.html',
        form=form
    )


@app.route('/login', methods=['GET', 'POST'])
def login():

    if 'user_id' in session:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            username=form.username.data
        ).first()

        if user and bcrypt.check_password_hash(
                user.password,
                form.password.data):

            session['user_id'] = user.id
            session['username'] = user.username

            flash("Login Successful!", "success")
            return redirect(url_for('index'))

        flash("Invalid Username or Password", "danger")

    return render_template(
        'login.html',
        form=form
    )


@app.route('/logout')
def logout():

    session.pop('user_id', None)
    session.pop('username', None)

    flash("Logged out successfully!", "info")

    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def index():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        diary_text = request.form['diary_entry']

        category = categorize_entry(diary_text)
        sentiment = analyze_sentiment(diary_text)

        entry = DiaryEntry(
            text=diary_text,
            category=category,
            sentiment=sentiment,
            user_id=session['user_id']
        )

        db.session.add(entry)
        db.session.commit()

        flash("Entry added successfully!", "success")

        return redirect(url_for('entries'))

    return render_template('index.html')


@app.route('/entries')
def entries():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')

    diary_entries = DiaryEntry.query.filter_by(
        user_id=session['user_id']
    ).order_by(
        DiaryEntry.timestamp.desc()
    )

    if search_query:
        diary_entries = diary_entries.filter(
            DiaryEntry.text.contains(search_query)
        )

    diary_entries = diary_entries.all()

    return render_template(
        'entries.html',
        diary_entries=diary_entries,
        search_query=search_query
    )


@app.route('/delete_entry/<int:index>', methods=['POST'])
def delete_entry(index):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    entry = DiaryEntry.query.filter_by(
        id=index,
        user_id=session['user_id']
    ).first()

    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Entry deleted successfully!", "success")
    else:
        flash("Entry not found.", "danger")

    return redirect(url_for('entries'))


# -------------------- Run --------------------

if __name__ == '__main__':
    app.run(debug=True)