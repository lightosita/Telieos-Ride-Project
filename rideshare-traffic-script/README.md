# SwiftRide Traffic Generator

This script simulates real-time traffic for the SwiftRide ride-sharing platform in **Lagos, Nigeria**. It generates realistic rider and driver activities to test the microservices architecture.

## Features

- **Realistic Simulation**: Simulates the entire ride lifecycle:
    - **Registration**: Registers new Riders and Drivers.
    - **Requests**: Riders request rides with random pickup/dropoff locations in Lagos.
    - **Acceptance**: Drivers accept ride requests (simulated delay for realism).
    - **Trip Progress**: Simulates driver arriving, starting the trip, and completing the trip.
- **Microservice Interaction**: Directly interacts with:
    - **Rider Service**: Authentication & Ride Requests.
    - **Driver Service**: Authentication, Location Updates, Availability & Ride Acceptance.
    - **Trip Service**: Trip status updates (Arrived, Started, Completed).
- **Concurrency**: Uses threading to simulate multiple riders and drivers simultaneously.
- **Robustness**: Handles rate limits (429) and network delays automatically.

## Prerequisites

- **Python 3.x**
- **SwiftRide Microservices** running locally (or reachable via network).
    - Rider Service: `http://localhost:3001`
    - Driver Service: `http://localhost:3003`
    - Trip Service: `http://localhost:3005`

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/teleios-community/rideshare-traffic-script.git
    cd rideshare-traffic-script
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r traffic_requirements.txt
    ```

## Usage

1.  **Ensure all SwiftRide services are running**.
2.  **Run the script**:
    ```bash
    python traffic_generator.py
    ```

## Logic Flow

1.  **Bootstrapping**: Registers 10 Riders and 5 Drivers.
2.  **Simulation Loop**:
    - Picks a random Rider.
    - Rider requests a ride (Pickup/Dropoff in Lagos).
    - Script waits 5 seconds (to allow database propagation).
    - An available Driver accepts the ride.
    - Driver updates status: `Arrived` -> `Started` -> `Completed`.
    - Driver becomes available again.
    - Repeats indefinitely.
