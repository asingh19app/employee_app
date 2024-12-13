from math import radians,sin,cos,sqrt,atan2

#Location validation function
def haversine(lat1, lon1, lat2, lon2):
    #radius of earth in km
    R = 6371

    #convert latitude difference to radians
    dlat = radians(lat2 - lat1) 

    #convert longitude difference to radians
    dlon = radians(lon2 - lon1)


    a = sin(dlat / 2 ) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2

    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


#WORK LOCATION COORDINATES AND RADIUS ALLOWED
MERCY_UNIV_LAT = 41.0130
MERCY_UNIV_LONG = -73.8726
ALLOWED_RADIUS_KM = 0.5


#example users
users = [
    {'name':'A', 'lat':41.0140, 'lon':-73.8720},
    {'name':'B', 'lat':41.0160, 'lon':-75.8740},
    {'name':'C', 'lat':41.0135, 'lon':-73.8728}

]

for user in users:
    distance = haversine(MERCY_UNIV_LAT,MERCY_UNIV_LONG, user['lat'], user['lon'])
    if distance <= ALLOWED_RADIUS_KM:
        print(f"User {user['name']} is within radius: {distance:.2f} km")
    else:
        print(f"User {user['name']} is outside radius: {distance:.2f} km")

