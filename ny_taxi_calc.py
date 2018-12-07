import statsmodels.api as sm
from scipy import stats
from sklearn.tree import DecisionTreeRegressor
from flask import Flask,Response,send_from_directory,redirect
import pickle
from datetime import datetime
from flask import json
from flask import request
from flask import render_template
import os
import numpy as np
import requests

def extract_time(time_str,time_format="%Y-%m-%d %H:%M:%S UTC"):
    datetime_object = datetime.strptime(time_str, time_format)
    return (datetime_object.year,datetime_object.month,datetime_object.day,datetime_object.weekday(),datetime_object.hour)

def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))

def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)

app = Flask(__name__)

# load model
with open("all_model.pickle","rb") as file:
    (est2, est2b, est2c, regr_1d, regr_2d) = pickle.load(file)

@app.route('/', methods=['GET'])
def web_root():  # pragma: no cover
    return redirect("/taxi/index.html", code=302)

@app.route('/taxi/', methods=['GET'])
def taxi_web():  # pragma: no cover
    return redirect("/taxi/index.html", code=302)

@app.route('/taxi/<path:path>')
def send_js(path):
    return send_from_directory('taxi_web', path)

@app.route("/calculate_fare",methods=["POST"])
def calculate_fare():
    if request.headers['Content-Type'] == 'application/json':
        parameters = request.json
        print(parameters)
        start_loc = parameters["start"]
        dest_loc = parameters["dest"]
        pickup_time = parameters["pickup_time"]
        pass_count = parameters["passenger_count"]

        my_time = extract_time(pickup_time,"%Y/%m/%d %H:%M")

        # calculate distance using gogole api
        dist_url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins="+str(start_loc["lat"])+","+str(start_loc["lng"])+"&destinations="+str(dest_loc["lat"])+","+str(dest_loc["lng"])+"&key=AIzaSyA7_KvLPtVesTg7NLxXnL_czMlX7GcyXXw";
        r = requests.get(url=dist_url)

        # extracting data in json format
        data = r.json()

        print(data)
        dist_mile = float(data["rows"][0]["elements"][0]["distance"]["text"].replace(" mi",""))
        dist_text = data["rows"][0]["elements"][0]["distance"]["text"]
        start_place = data["origin_addresses"][0]
        dest_place = data["destination_addresses"][0]
        duration = data["rows"][0]["elements"][0]["duration"]["text"]
        #print(dist_mile)
        """         
        pickup_latitude
        pickup_longitude
        dropoff_latitude
        dropoff_longitude
        passenger_count
        distance
        year
        month
        dayofweek
        hour
        """

        max_lat = 40.9
        min_lat = 40.6
        max_lon = -73.7
        min_lon = -74.1
        type = 0

        # check if the location between NY City Range
        # make prediction using location as well
        if ((start_loc["lat"]>min_lat)&
           (start_loc["lat"]<max_lat)&
           (dest_loc["lat"]>min_lat)&
           (dest_loc["lat"]<max_lat)&
           (start_loc["lng"]>min_lon)&
           (start_loc["lng"]<max_lon)&
           (dest_loc["lng"]>min_lon)&
           (dest_loc["lng"]<max_lon)):
            my_X = np.zeros((1,10));
            my_X[0,0] = start_loc["lat"]
            my_X[0,1] = start_loc["lng"]
            my_X[0,2] = dest_loc["lat"]
            my_X[0,3] = dest_loc["lng"]
            my_X[0,4] = int(pass_count)
            my_X[0,5] = dist_mile
            my_X[0,6] = my_time[0]
            my_X[0,7] = my_time[1]
            my_X[0,8] = my_time[3]
            my_X[0,9] = my_time[4]

            #my_xc = sm.add_constant(my_X)

            fare_pred = regr_1d.predict(my_X)

        else:
            type=1
            my_X = np.zeros((2,6))
            my_X[0,0] = int(pass_count)
            my_X[0,1] = dist_mile
            my_X[0,2] = my_time[0]
            my_X[0,3] = my_time[1]
            my_X[0,4] = my_time[3]
            my_X[0,5] = my_time[4]

            my_xc = sm.add_constant(my_X)
            print(my_xc)
            print(my_xc.shape)

            fare_pred = est2c.predict(my_xc)

        print(fare_pred)

        #distance_api =

        #return "data:image/png;base64,{}".format(image_encoded)
        #return fare
        return json.dumps({"status": 0,"type":type,"start":start_place,"dest":dest_place,"distance":dist_text,"duration":duration,"fare":fare_pred.tolist()[0]})
    return json.dumps({"status": 1})

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port=5500)
