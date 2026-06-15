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
from datetime import datetime, timedelta
from collections import OrderedDict, Counter
import os
from dotenv import load_dotenv
import truststore
import google.genai as genai
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# Trust the OS (Windows) certificate store so HTTPS works behind a
# corporate proxy that intercepts TLS. This is what fixes the Gemini SDK's
# "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate" errors.
truststore.inject_into_ssl()

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

# -------------------- Gemini Setup --------------------

load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fallback shown when there isn't enough material for a meaningful insight.
INSUFFICIENT_ENTRIES_MSG = (
    "Write at least 3 entries this week to unlock your AI insight."
)

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

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
    sentiment_score = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class WeeklyInsight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    insight_text = db.Column(db.Text, nullable=False)
    generated_on = db.Column(db.DateTime, default=lambda: datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def ensure_schema():
    """Migration-safe schema setup for SQLite.

    db.create_all() only creates missing tables; it will NOT add new
    columns to a table that already exists. For an existing site.db that
    predates the sentiment_score column we add it via ALTER TABLE, guarding
    against the case where it is already present.
    """
    db.create_all()

    inspector = db.inspect(db.engine)
    existing_columns = {
        col['name'] for col in inspector.get_columns('diary_entry')
    }

    if 'sentiment_score' not in existing_columns:
        with db.engine.begin() as connection:
            connection.execute(
                db.text('ALTER TABLE diary_entry ADD COLUMN sentiment_score FLOAT')
            )


with app.app_context():
    ensure_schema()

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
    compound = sentiment_scores['compound']

    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return sentiment, compound


def backfill_sentiment_scores():
    """Compute sentiment_score for entries created before the column existed.

    Entries saved prior to the schema migration have sentiment_score = NULL
    and are skipped by the dashboard. We recompute the VADER compound score
    from their stored text so historical entries appear in the trend chart.
    """
    legacy_entries = DiaryEntry.query.filter(
        DiaryEntry.sentiment_score.is_(None)
    ).all()

    if not legacy_entries:
        return

    for entry in legacy_entries:
        entry.sentiment_score = sid.polarity_scores(entry.text)['compound']

    db.session.commit()


with app.app_context():
    backfill_sentiment_scores()


# -------------------- AI Weekly Insights --------------------

def generate_weekly_insight(user_id):
    entries = (
        DiaryEntry.query
        .filter_by(user_id=user_id)
        .order_by(DiaryEntry.timestamp.desc())
        .limit(7)
        .all()
    )

    if len(entries) < 3:
        return INSUFFICIENT_ENTRIES_MSG

    if not GEMINI_API_KEY:
        return (
            "AI insights are unavailable: the GEMINI_API_KEY is not "
            "configured. Add it to your .env file to enable this feature."
        )

    entry_lines = []
    for entry in entries:
        date_str = entry.timestamp.strftime('%Y-%m-%d')
        if entry.sentiment_score is not None:
            score_str = f"{entry.sentiment_score:.2f}"
        else:
            score_str = "N/A"
        snippet = entry.text[:300].replace("\n", " ").strip()
        entry_lines.append(
            f"- Date: {date_str} | Category: {entry.category} | "
            f"Sentiment: {entry.sentiment} (score {score_str})\n"
            f"  Entry: {snippet}"
        )
    entries_block = "\n".join(entry_lines)

    prompt = (
        "You are a compassionate journaling coach. Based on the following "
        "journal entries from the past week, provide a personal insight in "
        "exactly 3 short paragraphs:\n\n"
        "Paragraph 1 — Emotional pattern: Describe the emotional arc or "
        "dominant mood across the week.\n"
        "Paragraph 2 — Recurring themes: Identify 2-3 topics or situations "
        "that appear repeatedly.\n"
        "Paragraph 3 — Actionable suggestion: Give one specific, practical "
        "suggestion the person can act on this week.\n\n"
        "Keep the tone warm, non-judgmental, and personal. Do not use bullet "
        "points. Do not use headings. Write as if you are speaking directly "
        "to the person.\n\n"
        "Journal entries:\n"
        f"{entries_block}"
    )

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as error:
        return (
            "Could not generate your insight right now. Please try again "
            f"later. ({error})"
        )


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
        sentiment, sentiment_score = analyze_sentiment(diary_text)

        entry = DiaryEntry(
            text=diary_text,
            category=category,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
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


@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = datetime.now().date()

    # Pull everything in the widest window (30 days) once, then derive both
    # the 7-day and 30-day views from it in Python.
    window_start = today - timedelta(days=29)
    entries = (
        DiaryEntry.query
        .filter_by(user_id=session['user_id'])
        .filter(
            DiaryEntry.timestamp
            >= datetime.combine(window_start, datetime.min.time())
        )
        .order_by(DiaryEntry.timestamp.asc())
        .all()
    )

    # Bucket entries by calendar day: scores, category counts, and total count.
    day_data = {}
    for entry in entries:
        day = entry.timestamp.date()
        bucket = day_data.setdefault(
            day, {'scores': [], 'cats': Counter(), 'count': 0}
        )
        bucket['count'] += 1
        if entry.category:
            bucket['cats'][entry.category] += 1
        if entry.sentiment_score is not None:
            bucket['scores'].append(entry.sentiment_score)

    def build_dataset(num_days, label_fmt):
        """Build a continuous-calendar dataset of the last `num_days` days.

        Every day in the range is included (missing days get a null score),
        so the x-axis is gap-free and the rolling average is a true
        calendar-day window.
        """
        start = today - timedelta(days=num_days - 1)
        day_list = [start + timedelta(days=i) for i in range(num_days)]

        dates = [d.strftime(label_fmt) for d in day_list]

        daily_scores = []
        for d in day_list:
            scores = day_data.get(d, {}).get('scores')
            if scores:
                daily_scores.append(round(sum(scores) / len(scores), 4))
            else:
                daily_scores.append(None)

        # 7-day rolling average over the per-day averages. First 6 days are
        # null (no full window); within a window we average the days that
        # actually have data.
        rolling_avg = []
        window = 7
        for i in range(len(daily_scores)):
            if i + 1 < window:
                rolling_avg.append(None)
                continue
            window_slice = [
                s for s in daily_scores[i - window + 1:i + 1]
                if s is not None
            ]
            if window_slice:
                rolling_avg.append(
                    round(sum(window_slice) / len(window_slice), 4)
                )
            else:
                rolling_avg.append(None)

        # Summary stats over the window.
        window_scores = []
        cat_counter = Counter()
        total_entries = 0
        for d in day_list:
            bucket = day_data.get(d)
            if not bucket:
                continue
            total_entries += bucket['count']
            window_scores.extend(bucket['scores'])
            cat_counter.update(bucket['cats'])

        avg_sentiment = (
            round(sum(window_scores) / len(window_scores), 4)
            if window_scores else 0.0
        )
        most_common_category = (
            cat_counter.most_common(1)[0][0]
            if cat_counter else "N/A"
        )

        return {
            'dates': dates,
            'daily_scores': daily_scores,
            'rolling_avg': rolling_avg,
            'total_entries': total_entries,
            'avg_sentiment': avg_sentiment,
            'most_common_category': most_common_category,
        }

    # 7-day labels: "Mon 09" (weekday + day). 30-day labels: "Jun 09"
    # (axis ticks are hidden in the template, used only for tooltips).
    data_7 = build_dataset(7, '%a %d')
    data_30 = build_dataset(30, '%b %d')

    return render_template(
        'dashboard.html',
        data_7=data_7,
        data_30=data_30
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


@app.route('/insights')
def insights():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cutoff = datetime.now() - timedelta(days=7)

    # Use a cached insight if one was generated within the last 7 days.
    cached = (
        WeeklyInsight.query
        .filter_by(user_id=user_id)
        .filter(WeeklyInsight.generated_on >= cutoff)
        .order_by(WeeklyInsight.generated_on.desc())
        .first()
    )

    if cached:
        return render_template(
            'insights.html',
            insight_text=cached.insight_text,
            generated_on=cached.generated_on
        )

    insight_text = generate_weekly_insight(user_id)

    # Don't cache the "not enough entries" placeholder — we want it to
    # disappear as soon as the user has written enough entries.
    if insight_text == INSUFFICIENT_ENTRIES_MSG:
        return render_template(
            'insights.html',
            insight_text=insight_text,
            generated_on=None
        )

    insight = WeeklyInsight(
        insight_text=insight_text,
        user_id=user_id
    )
    db.session.add(insight)
    db.session.commit()

    return render_template(
        'insights.html',
        insight_text=insight.insight_text,
        generated_on=insight.generated_on
    )


@app.route('/insights/refresh', methods=['POST'])
def insights_refresh():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    WeeklyInsight.query.filter_by(
        user_id=session['user_id']
    ).delete()
    db.session.commit()

    return redirect(url_for('insights'))


# -------------------- Run --------------------

if __name__ == '__main__':
    app.run(debug=True)