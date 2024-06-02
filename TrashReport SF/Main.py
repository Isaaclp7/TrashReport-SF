from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, render_template, flash, request  # Import 'request'
from flask_sqlalchemy import SQLAlchemy
from forms import RequestForm
import os
from PIL import Image
from PIL.ExifTags import TAGS
import logging
from PIL.ExifTags import TAGS, GPSTAGS
from werkzeug.utils import secure_filename
from flask import jsonify
from flask_session import Session

logging.basicConfig(filename='app.log', level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = "hello"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(minutes=20000)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'  # Define the upload folder
app.static_folder = 'static'  # Configure Flask to serve static files from the 'static' folder
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'

# Set the session expiry time to 1 day (in seconds)
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 86400 seconds = 1 day

Session(app)


db = SQLAlchemy(app)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=True)
    picture_path = db.Column(db.String(255), nullable=True)  # Store the file path instead of the file itself
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    request_latitude = db.Column(db.String(255), nullable=True)
    request_longitude = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"Report('{self.title}', '{self.picture_path}', '{self.date_posted}')"

def get_exif_data(image_path):
    # Open the image file
    image = Image.open(image_path)
    
    # Extract Exif data
    exif_data = image._getexif()
    return exif_data

def get_gps_info(exif_data):
    gps_info = {}

    # Check if GPS-related tags exist in the exif_data dictionary
    if exif_data:
        gps_tags = [34853, 34857]  # Assuming these tags contain GPS data
        for tag in gps_tags:
            if tag in exif_data:
                gps_info[tag] = exif_data[tag]

    return gps_info


def get_location(exif_data):
    # Get latitude and longitude from GPS data
    gps_info = exif_data.get(34853)
    latitude_ref = gps_info.get(1)
    latitude_tuple = gps_info.get(2)
    longitude_ref = gps_info.get(3)
    longitude_tuple = gps_info.get(4)

    # If GPS data is not available, return None
    if not (latitude_ref and latitude_tuple and longitude_ref and longitude_tuple):
        return None, None

    # Convert latitude to decimal format
    lat_degrees = latitude_tuple[0] + latitude_tuple[1] / 60.0 + latitude_tuple[2] / 3600.0

    # Adjust latitude based on reference direction
    if latitude_ref == 'S':
        lat_decimal = -lat_degrees
    else:
        lat_decimal = lat_degrees

    # Convert longitude to decimal format
    lon_degrees = longitude_tuple[0] + longitude_tuple[1] / 60.0 + longitude_tuple[2] / 3600.0

    # Adjust longitude based on reference direction
    if longitude_ref == 'W':
        lon_decimal = -lon_degrees
    else:
        lon_decimal = lon_degrees

    return lat_decimal, lon_decimal


@app.route("/")
def home():
    return redirect(url_for("map"))

@app.route('/api/requests')
def api_requests():
    requests = Report.query.all()
    serialized_requests = [{'title': request.title, 'latitude': request.request_latitude, 'longitude': request.request_longitude, 'picture_path': request.picture_path} for request in requests]
    return jsonify(serialized_requests)

@app.route("/map")
def map():
    requests = Report.query.all()
    return render_template("map.html", requests=requests)

@app.route("/requests")
def requests_page():
    requests = Report.query.all()
    return render_template("requests.html", requests=requests)

@app.route("/request/new", methods=['GET', 'POST'])
def new_request():
    form = RequestForm()
    if form.validate_on_submit():
        if 'picture' in request.files:
            file = request.files['picture']
            if file.filename != '':
                # Ensure the 'static/uploads' directory exists
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)

                # Save the uploaded file with its original filename
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                os.chmod(file_path, 0o644)

                # Extract Exif data from the image
                exif_data = get_exif_data(file_path)
                gps_info = get_gps_info(exif_data)

                # Extract location from Exif data
                latitude, longitude = get_location(exif_data)
                latitude = str(latitude) if latitude is not None else ""
                longitude = str(longitude) if longitude is not None else ""
                # If GPS data is not accessible, abort the request and return an error message
                if latitude is None or longitude is None:
                    error_message = "GPS data is not accessible in the uploaded image. If using an iphone, please allow your camera app location access."
                    return jsonify({'error': error_message}), 400

                # Construct the relative path in the database
                picture_path = 'uploads/' + filename

                # Create a new report instance
                report = Report(
                    title=form.title.data,
                    picture_path=picture_path,
                    request_latitude=latitude,
                    request_longitude=longitude,
                )
                db.session.add(report)
                db.session.commit()
                logging.debug(f'Report saved: {report}')  # Log the report
                flash('Your report has been created!')
                return redirect(url_for('requests_page'))
    return render_template('create_request.html', title='New Request', form=form)
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)