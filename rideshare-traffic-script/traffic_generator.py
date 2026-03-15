import requests
import time
import random
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

# Config
RIDER_SERVICE_URL = "http://localhost:3001/api/v1/riders"
# Driver Service is on 3003 based on docker-compose
DRIVER_SERVICE_URL = "http://localhost:3003/api/v1/drivers" 
# Trip Service is on 3005 based on app.py and docker-compose
TRIP_SERVICE_URL = "http://localhost:3005/api/v1/trips" 

NUM_RIDERS = 10
NUM_DRIVERS = 5
DELAY_BETWEEN_ACTIONS = 2

# Lagos Coordinates
LAGOS_LAT = 6.5244
LAGOS_LNG = 3.3792
COORD_SPREAD = 0.05 # Approx 5km spread

def generate_lagos_location():
    return {
        "lat": str(LAGOS_LAT + random.uniform(-COORD_SPREAD, COORD_SPREAD)),
        "lng": str(LAGOS_LNG + random.uniform(-COORD_SPREAD, COORD_SPREAD)),
        "address": "Random Lagos Street"
    }

def generate_random_rider():
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"rider_{unique_id}@example.com",
        "password": "password123",
        "firstName": f"Rider{unique_id}",
        "lastName": "Lagos",
        "phoneNumber": f"80{random.randint(10000000, 99999999)}" # Nigerian phone format
    }

def generate_random_driver():
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"driver_{unique_id}@example.com",
        "password": "password123",
        "firstName": f"Driver{unique_id}",
        "lastName": "Lagos",
        "phoneNumber": f"81{random.randint(10000000, 99999999)}",
        "licenseNumber": f"LAG-{unique_id.upper()}",
        "vehiclePlate": f"LND-{random.randint(100, 999)}-{random.choice(['AA', 'BB', 'CC'])}",
        "vehicleType": random.choice(["SEDAN", "SUV", "VAN", "LUXURY", "ELECTRIC"]),
        "vehicleMake": "Toyota",
        "vehicleModel": "Corolla",
        "vehicleYear": 2015
    }

class TrafficGenerator:
    def __init__(self):
        self.riders = []
        self.drivers = []
        self.available_drivers = [] # Stack of available drivers
        self.lock = threading.Lock()

    def register_rider(self):
        data = generate_random_rider()
        try:
            # print(f"Registering rider: {data['email']}")
            response = requests.post(f"{RIDER_SERVICE_URL}/auth/register", json=data)
            if response.status_code == 201:
                res_json = response.json()
                rider_data = res_json.get('data', {})
                self.riders.append({
                    "token": rider_data.get('token'),
                    "id": rider_data.get('rider', {}).get('id')
                })
                print(f"Rider registered: {data['email']}")
            else:
                print(f"Failed to register rider: {response.text}")
        except Exception as e:
            print(f"Error registering rider: {e}")

    def register_driver(self):
        data = generate_random_driver()
        try:
            # print(f"Registering driver: {data['email']}")
            response = requests.post(f"{DRIVER_SERVICE_URL}/auth/register", json=data)
            if response.status_code == 201:
                res_json = response.json()
                driver_data = res_json.get('data', {})
                driver_obj = {
                    "token": driver_data.get('token'),
                    "id": driver_data.get('driver', {}).get('id'),
                    "email": data['email']
                }
                self.drivers.append(driver_obj)
                
                # Make driver available immediately
                self.set_driver_available(driver_obj)
                print(f"Driver registered: {data['email']}")
            else:
                print(f"Failed to register driver: {response.text}")
        except Exception as e:
            print(f"Error registering driver: {e}")

    def set_driver_available(self, driver):
        headers = {"Authorization": f"Bearer {driver['token']}"}
        try:
            # Update location
            loc = generate_lagos_location()
            requests.post(f"{DRIVER_SERVICE_URL}/location", json={
                "latitude": float(loc['lat']),
                "longitude": float(loc['lng']),
                "heading": 0,
                "speedKmh": 0
            }, headers=headers)

            # Update availability
            requests.patch(f"{DRIVER_SERVICE_URL}/availability", json={"isAvailable": True}, headers=headers)
            
            with self.lock:
                if driver not in self.available_drivers:
                    self.available_drivers.append(driver)
            
            # print(f"Driver {driver['email']} is now available")
        except Exception as e:
            print(f"Error setting driver availability: {e}")

    def simulate_ride_lifecycle(self, rider):
        if not rider: return

        rider_headers = {"Authorization": f"Bearer {rider['token']}"}
        
        # 1. Request Ride
        trip_id = None
        ride_request_id = None
        assigned_driver = None

        try:
            pickup = generate_lagos_location()
            dropoff = generate_lagos_location()
            
            print(f"Rider {rider['id'][:8]} requesting ride...")
            req_data = {
                "pickup_lat": pickup['lat'],
                "pickup_lng": pickup['lng'],
                "pickup_address": pickup['address'],
                "dropoff_lat": dropoff['lat'],
                "dropoff_lng": dropoff['lng'],
                "dropoff_address": dropoff['address'],
                "fare": str(random.randint(500, 5000)), # Naira
                "vehicle_type": "standard"
            }
            res = requests.post(f"{RIDER_SERVICE_URL}/ride-requests", json=req_data, headers=rider_headers)
            
            if res.status_code == 202: # Accepted
                res_json = res.json()
                ride_request_id = res_json.get('data', {}).get('rideRequestId')
                print(f"Ride Requested! ID: {ride_request_id}")
                time.sleep(5) # Wait 5s for DB propagation/commit
            elif res.status_code == 429:
                print("Rate limit hit (429). Cooling down...")
                time.sleep(10)
                return
            else:
                print(f"Ride request failed: {res.text}")
                return

        except Exception as e:
            print(f"Error during ride request: {e}")
            return

        # 2. Assign Driver (Simulation Magic)
        with self.lock:
            if self.available_drivers:
                assigned_driver = self.available_drivers.pop(0)
            else:
                print("No drivers available for this ride.")
                return

        driver_headers = {"Authorization": f"Bearer {assigned_driver['token']}"}

        # 3. Driver Accepts Ride
        try:
            print(f"Driver {assigned_driver['email']} accepting request {ride_request_id}...")
            # Driver Service: POST /ride-requests/:id/accept
            accept_res = requests.post(
                f"{DRIVER_SERVICE_URL}/ride-requests/{ride_request_id}/accept",
                headers=driver_headers
            )
            
            if accept_res.status_code == 200:
                trip_data = accept_res.json().get('data', {}).get('trip', {})
                trip_id = trip_data.get('id')
                print(f"Ride accepted! Trip ID: {trip_id}")
            elif accept_res.status_code == 429:
                 print("Driver accept rate limited. Cooling down...")
                 self.set_driver_available(assigned_driver) 
                 time.sleep(5)
                 return
            else:
                print(f"Driver accept failed: {accept_res.text}")
                # Return driver to pool
                self.set_driver_available(assigned_driver) 
                return
        except Exception as e:
            print(f"Error accepting ride: {e}")
            self.set_driver_available(assigned_driver)
            return

        # 4. Simulate Trip Progress (Arrived -> Started -> Completed)
        try:
            # Arrived
            time.sleep(2)
            print(f"Driver {assigned_driver['email']} arrived.")
            requests.post(f"{TRIP_SERVICE_URL}/driver/mark-arrived", 
                          json={"ride_request_id": ride_request_id}, headers=driver_headers)

            # Started
            time.sleep(2)
            print(f"Trip {trip_id} started.")
            requests.post(f"{TRIP_SERVICE_URL}/driver/mark-started", 
                          json={"ride_request_id": ride_request_id}, headers=driver_headers)
            
            # Driving...
            time.sleep(3) 
            
            # Completed
            print(f"Trip {trip_id} completed.")
            requests.post(f"{TRIP_SERVICE_URL}/driver/mark-completed", 
                          json={"ride_request_id": ride_request_id}, headers=driver_headers)

            # Make driver available again
            self.set_driver_available(assigned_driver)

        except Exception as e:
            print(f"Error during trip progress: {e}")
            self.set_driver_available(assigned_driver)


    def run(self):
        print("Starting Lagos Traffic Generator...")
        print(f"Rider Service: {RIDER_SERVICE_URL}")
        print(f"Driver Service: {DRIVER_SERVICE_URL}")
        print(f"Trip Service: {TRIP_SERVICE_URL}")

        # Register entities
        with ThreadPoolExecutor(max_workers=5) as executor:
            print("Registering users...")
            for _ in range(NUM_RIDERS): executor.submit(self.register_rider)
            for _ in range(NUM_DRIVERS): executor.submit(self.register_driver)
        
        time.sleep(2) 

        print(f"Registered {len(self.riders)} riders and {len(self.drivers)} drivers.")

        while True:
            if self.riders and self.available_drivers:
                # Pick a random rider to go on a trip
                rider = random.choice(self.riders)
                # Run ride in a thread to allow concurrency
                t = threading.Thread(target=self.simulate_ride_lifecycle, args=(rider,))
                t.start()
            else:
                if not self.available_drivers:
                    print("Waiting for drivers to become available...")
            
            # Increase loop delay to reduce rate limiting issues
            time.sleep(5)

if __name__ == "__main__":
    generator = TrafficGenerator()
    generator.run()
