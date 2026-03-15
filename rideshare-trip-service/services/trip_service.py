import logging
from typing import Optional, Dict, Any, List
import json
from decimal import Decimal

from utils.redis_client import redis_client
from utils.database import get_db_connection

logger = logging.getLogger(__name__)

class TripService:
    """
    Business logic for the Trip Service.
    
    Resolved Issues:
    - Fixed driver_info being NULL in database
    - Fixed JSON field name consistency (licensePlate vs license_plate)
    - Added method to fix existing trips with missing driver_info
    """

    COMMISSION_RATE = Decimal('0.20')

    # ────────────────────────────────────────────────
    # 1. TRIP CREATION & ENRICHMENT (FIXED)
    # ────────────────────────────────────────────────
    @staticmethod
    def _clean_trip_dict(trip: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
        """Clean up types for JSON serialization and ensure key consistency"""
        # Ensure all expected numeric fields are floats
        numeric_fields = ['estimated_fare', 'actual_fare', 'distance_km', 'duration_minutes', 'rider_rating', 'driver_payment_amount', 'platform_commission']
        for field in numeric_fields:
            if field in trip:
                trip[field] = float(trip[field]) if trip[field] is not None else None

        # Convert UUIDs to strings
        uuid_fields = ['id', 'ride_request_id', 'rider_id', 'driver_id']
        for field in uuid_fields:
            if field in trip and trip[field]:
                trip[field] = str(trip[field])

        # Aliases for convenience
        if 'id' in trip:
            trip['trip_id'] = trip.get('trip_id', str(trip['id']))

        # Convert datetimes to ISO strings
        date_fields = ['started_at', 'completed_at', 'created_at', 'updated_at', 'payment_processed_at']
        for field in date_fields:
            if field in trip and hasattr(trip[field], 'isoformat'):
                trip[field] = trip[field].isoformat()

        # Parse driver_info JSON
        if 'driver_info' in trip:
            if trip['driver_info'] is None:
                trip['driver_info'] = {}
            elif isinstance(trip['driver_info'], str):
                try:
                    trip['driver_info'] = json.loads(trip['driver_info'])
                except (json.JSONDecodeError, TypeError):
                    trip['driver_info'] = {}

        return trip

    @staticmethod
    def create_trip_from_event(event_data: Dict[str, Any]) -> Optional[str]:
        ride_request_id = (
            event_data.get("ride_request_id")
            or event_data.get("request_id")
            or event_data.get("ride")
        )
        driver_id = event_data.get("driver_id") or event_data.get("driverId")
        rider_id = event_data.get("rider_id") or event_data.get("riderId")

        if not ride_request_id or not driver_id:
            logger.error(f"Missing IDs for trip. Ride: {ride_request_id}, Driver: {driver_id}")
            return None

        # Default driver info
        driver_info = {
            "name": "Unknown Driver",
            "phone": "",
            "rating": 4.8,
            "vehicle": "",
            "licensePlate": ""
        }

        # Try to fetch driver info from driver_service
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT first_name, last_name, phone, rating, 
                               vehicle_make, vehicle_model, license_plate 
                        FROM driver_service.drivers 
                        WHERE id = %s
                        """,
                        (driver_id,),
                    )
                    d = cur.fetchone()
                    if d:
                        # Build driver name
                        first_name = d[0] or ""
                        last_name = d[1] or ""
                        driver_name = f"{first_name} {last_name}".strip()
                        
                        # Build vehicle info
                        vehicle_make = d[4] or ""
                        vehicle_model = d[5] or ""
                        vehicle = f"{vehicle_make} {vehicle_model}".strip()
                        
                        driver_info = {
                            "name": driver_name if driver_name else "Unknown Driver",
                            "phone": d[2] or "",
                            "rating": float(d[3]) if d[3] is not None else 4.8,
                            "vehicle": vehicle,
                            "licensePlate": d[6] or ""
                        }
                        logger.info(f"Driver info fetched for {driver_id}: {driver_info}")
                    else:
                        logger.warning(f"Driver {driver_id} not found in database, using defaults")
        except Exception as e:
            logger.error(f"Driver enrichment failed: {e}")
            # Continue with default driver_info

        # Ensure driver_info is never None
        if not driver_info:
            driver_info = {
                "name": "Unknown Driver",
                "phone": "",
                "rating": 4.8,
                "vehicle": "",
                "licensePlate": ""
            }

        try:
            # Convert to JSON string
            driver_info_json = json.dumps(driver_info)
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trip_service.trips (
                            ride_request_id, rider_id, driver_id, 
                            pickup_lat, pickup_lng, pickup_address,
                            dropoff_lat, dropoff_lng, dropoff_address,
                            vehicle_type, estimated_fare, rider_name, 
                            rider_phone, rider_rating, driver_info, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'accepted')
                        ON CONFLICT (ride_request_id) DO UPDATE SET
                            driver_id     = EXCLUDED.driver_id,
                            driver_info   = EXCLUDED.driver_info,
                            status        = EXCLUDED.status,
                            updated_at    = CURRENT_TIMESTAMP
                        RETURNING id
                        """,
                        (
                            ride_request_id, rider_id, driver_id,
                            event_data.get("pickup_lat"), event_data.get("pickup_lng"), event_data.get("pickup_address"),
                            event_data.get("dropoff_lat"), event_data.get("dropoff_lng"), event_data.get("dropoff_address"),
                            event_data.get("vehicle_type", "sedan"), event_data.get("estimated_fare"),
                            event_data.get("rider_name", "Passenger"), event_data.get("rider_phone"),
                            event_data.get("rider_rating", 4.8), driver_info_json,
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    trip_id = str(row[0]) if row else None
                    if trip_id:
                        logger.info(f"Trip created/updated: {trip_id} for request {ride_request_id}")
                    return trip_id
        except Exception as e:
            logger.error(f"Trip upsert failed: {e}")
            return None

    # ────────────────────────────────────────────────
    # 2. STATUS TRANSITIONS & EVENT PUBLISHING
    # ────────────────────────────────────────────────
    @staticmethod
    def update_trip_status_by_request_id(
        ride_request_id: str, 
        new_status: str,
        distance_km: Optional[float] = None,
        duration_minutes: Optional[int] = None
    ) -> Optional[Dict]:
        allowed_prev = {
            "arrived":   ["pending", "accepted", "arrived"],
            "started":   ["accepted", "arrived", "started"],   # accepted → started (no 'arrived' in current flow)
            "completed": ["accepted", "arrived", "started", "completed"]
        }

        prev_statuses = allowed_prev.get(new_status)
        if not prev_statuses:
            logger.warning(f"Invalid status transition to {new_status}")
            return None

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Update SQL dynamically to include completion metrics if necessary
                    extra_fields = ""
                    params = [new_status]
                    
                    if new_status == 'completed':
                        extra_fields = ", completed_at = CURRENT_TIMESTAMP, actual_fare = estimated_fare, distance_km = %s, duration_minutes = %s"
                        params.extend([distance_km, duration_minutes])
                    
                    params.extend([ride_request_id, prev_statuses])

                    sql = f"""
                        UPDATE trip_service.trips 
                        SET status = %s, updated_at = CURRENT_TIMESTAMP {extra_fields}
                        WHERE ride_request_id = %s 
                          AND status = ANY(%s::text[])
                        RETURNING id, status, rider_id, driver_id
                    """
                    
                    cur.execute(sql, tuple(params))
                    row = cur.fetchone()
                    conn.commit()

                    if row:
                        event_payload = {
                            "trip_id": str(row[0]),
                            "new_status": row[1],
                            "rider_id": str(row[2]),
                            "driver_id": str(row[3]),
                            "event": "trip.status_updated"
                        }
                        
                        redis_client.publish_event("trip_service.updates", event_payload)
                        logger.info(f"Trip status updated: {ride_request_id} -> {new_status}")
                        
                        return {
                            "id": event_payload["trip_id"],
                            "status": event_payload["new_status"],
                            "rider_id": event_payload["rider_id"],
                            "driver_id": event_payload["driver_id"]
                        }
                    else:
                        logger.warning(f"No trip found or invalid status transition for {ride_request_id}")
        except Exception as e:
            logger.error(f"Status update failed for {ride_request_id}: {e}")
        return None

    # ────────────────────────────────────────────────
    # 3. ROUTE COMPATIBILITY WRAPPERS
    # ────────────────────────────────────────────────
    @staticmethod
    def mark_trip_arrived(rid: str):
        return TripService.update_trip_status_by_request_id(rid, "arrived")

    @staticmethod
    def mark_trip_started(rid: str):
        return TripService.update_trip_status_by_request_id(rid, "started")

    @staticmethod
    def complete_trip_by_request_id(
        ride_request_id: str, 
        distance_km: Optional[float] = None, 
        duration_minutes: Optional[int] = None
    ) -> Optional[str]:
        """Entry point for /trips/request/<id>/complete."""
        res = TripService.mark_trip_completed(
            ride_request_id, 
            distance_km=distance_km, 
            duration_minutes=duration_minutes
        )
        return res["id"] if res else None

    @staticmethod
    def mark_trip_completed(
        rid: str, 
        distance_km: Optional[float] = None, 
        duration_minutes: Optional[int] = None
    ):
        """Internal logic for completion, includes payment trigger."""
        res = TripService.update_trip_status_by_request_id(
            rid, 
            "completed", 
            distance_km=distance_km, 
            duration_minutes=duration_minutes
        )
        if res:
            TripService.process_trip_payment(res["id"])
        return res

    # ────────────────────────────────────────────────
    # 4. PAYMENT PROCESSING
    # ────────────────────────────────────────────────
    @staticmethod
    def process_trip_payment(trip_id: str) -> bool:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT driver_id, COALESCE(actual_fare, estimated_fare) FROM trip_service.trips WHERE id = %s",
                        (trip_id,)
                    )
                    trip = cur.fetchone()
                    if not trip or trip[1] is None: 
                        logger.warning(f"No fare found for trip {trip_id}")
                        return False

                    driver_id, fare = trip[0], Decimal(str(trip[1]))
                    commission = fare * TripService.COMMISSION_RATE
                    driver_net = fare - commission

                    cur.execute(
                        """
                        INSERT INTO trip_service.driver_accounts (driver_id, current_balance, total_earnings)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (driver_id) DO UPDATE SET
                            current_balance = driver_accounts.current_balance + EXCLUDED.current_balance,
                            total_earnings  = driver_accounts.total_earnings  + EXCLUDED.total_earnings,
                            last_payment_date = CURRENT_TIMESTAMP
                        """,
                        (driver_id, driver_net, driver_net),
                    )

                    # Update the trip record to reflect payment
                    cur.execute(
                        """
                        UPDATE trip_service.trips
                        SET payment_status = 'paid',
                            payment_processed_at = CURRENT_TIMESTAMP,
                            driver_payment_amount = %s,
                            platform_commission = %s
                        WHERE id = %s
                        """,
                        (driver_net, commission, trip_id)
                    )

                    # Log the transaction
                    cur.execute(
                        """
                        INSERT INTO trip_service.driver_transactions (driver_id, trip_id, amount, transaction_type, status, metadata)
                        VALUES (%s, %s, %s, 'trip_payment', 'completed', %s)
                        """,
                        (driver_id, trip_id, driver_net, json.dumps({
                            "total_fare": float(fare),
                            "commission": float(commission),
                            "commission_rate": float(TripService.COMMISSION_RATE)
                        }))
                    )

                    conn.commit()
                    logger.info(f"Payment processed and transaction logged for trip {trip_id}: driver={driver_id}, fare={fare}, net={driver_net}")
                    
                    # Publish payment processed event for real-time updates
                    try:
                        cur.execute("SELECT rider_id FROM trip_service.trips WHERE id = %s", (trip_id,))
                        rider_row = cur.fetchone()
                        rider_id_val = str(rider_row[0]) if rider_row else None
                        
                        event_payload = {
                            "trip_id": str(trip_id),
                            "driver_id": str(driver_id),
                            "rider_id": rider_id_val,
                            "amount": float(driver_net),
                            "event": "trip.payment_processed"
                        }
                        redis_client.publish_event("trip_service.updates", event_payload)
                    except Exception as e:
                        logger.error(f"Failed to publish payment event: {e}")

                    return True
        except Exception as e:
            logger.error(f"Payment failed for trip {trip_id}: {e}")
            return False

    # ────────────────────────────────────────────────
    # 5. FETCHING METHODS (FIXED)
    # ────────────────────────────────────────────────
    @staticmethod
    def get_trip_details_by_id(trip_id: str) -> Optional[Dict[str, Any]]:
        """Used by GET /trips/<trip_id>"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM trip_service.trips WHERE id = %s", (trip_id,)
                    )
                    columns = [desc[0] for desc in cur.description]
                    row = cur.fetchone()
                    if row:
                        trip = dict(zip(columns, row))
                        return TripService._clean_trip_dict(trip, columns)
        except Exception as e:
            logger.error(f"Error fetching trip details: {e}")
        return None

    @staticmethod
    def get_active_trip_for_rider(rider_id: str) -> Optional[Dict[str, Any]]:
        """Used by POST /active/rider"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, ride_request_id, status, driver_id, rider_id,
                               pickup_lat, pickup_lng, pickup_address,
                               dropoff_lat, dropoff_lng, dropoff_address,
                               vehicle_type, estimated_fare, rider_name, rider_phone, 
                               rider_rating, driver_info, created_at, updated_at,
                               started_at, completed_at
                        FROM trip_service.trips
                        WHERE rider_id = %s AND status IN ('accepted', 'arrived', 'started')
                        ORDER BY created_at DESC LIMIT 1
                        """, (rider_id,)
                    )
                    columns = [desc[0] for desc in cur.description]
                    row = cur.fetchone()
                    if not row: 
                        return None
                    
                    trip = dict(zip(columns, row))
                    
                    # Parse driver_info - handle NULL, string, or dict
                    driver_info = {}
                    driver_info_raw = trip.get('driver_info')
                    
                    if driver_info_raw is None:
                        # If driver_info is NULL, try to fetch from driver_service
                        driver_id = trip.get('driver_id')
                        if driver_id:
                            driver_info = TripService._get_driver_info_from_service(str(driver_id))
                    elif isinstance(driver_info_raw, str):
                        try:
                            driver_info = json.loads(driver_info_raw) if driver_info_raw else {}
                        except json.JSONDecodeError:
                            driver_info = {}
                    else:
                        driver_info = driver_info_raw or {}
                    
                    # Ensure license plate consistency
                    license_plate = (
                        driver_info.get("licensePlate") or 
                        driver_info.get("license_plate") or 
                        ""
                    )
                    
                    # Construct clean result
                    cleaned_trip = TripService._clean_trip_dict(trip, columns)
                    
                    # Add camelCase Aliases for frontend compatibility
                    cleaned_trip["riderId"] = cleaned_trip.get("rider_id")
                    cleaned_trip["rideRequestId"] = cleaned_trip.get("ride_request_id")
                    cleaned_trip["pickupLat"] = cleaned_trip.get("pickup_lat")
                    cleaned_trip["pickupLng"] = cleaned_trip.get("pickup_lng")
                    cleaned_trip["pickupAddress"] = cleaned_trip.get("pickup_address")
                    cleaned_trip["dropoffLat"] = cleaned_trip.get("dropoff_lat")
                    cleaned_trip["dropoffLng"] = cleaned_trip.get("dropoff_lng")
                    cleaned_trip["dropoffAddress"] = cleaned_trip.get("dropoff_address")
                    cleaned_trip["vehicleType"] = cleaned_trip.get("vehicle_type")
                    cleaned_trip["estimatedFare"] = cleaned_trip.get("estimated_fare")
                    
                    cleaned_trip["driverInfo"] = {
                        "name": driver_info.get("name", "Unknown Driver"),
                        "phone": driver_info.get("phone", ""),
                        "rating": float(driver_info.get("rating")) if driver_info.get("rating") is not None else 4.8,
                        "vehicle": driver_info.get("vehicle", ""),
                        "licensePlate": license_plate,
                    }
                    
                    return cleaned_trip
        except Exception as e:
            logger.error(f"Error fetching rider active trip: {e}", exc_info=True)
            return None

    @staticmethod
    def get_active_trip_for_driver(driver_id: str) -> Optional[Dict[str, Any]]:
        """Used by POST /active/driver"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT *
                        FROM trip_service.trips
                        WHERE driver_id = %s AND status IN ('accepted', 'arrived', 'started')
                        ORDER BY created_at DESC LIMIT 1
                        """, (driver_id,)
                    )
                    columns = [desc[0] for desc in cur.description]
                    row = cur.fetchone()
                    if not row: 
                        return None
                    
                    trip = dict(zip(columns, row))
                    cleaned_trip = TripService._clean_trip_dict(trip, columns)

                    # CamelCase aliases for frontend
                    cleaned_trip["riderId"] = cleaned_trip.get("rider_id")
                    cleaned_trip["rideRequestId"] = cleaned_trip.get("ride_request_id")
                    cleaned_trip["pickupLat"] = cleaned_trip.get("pickup_lat")
                    cleaned_trip["pickupLng"] = cleaned_trip.get("pickup_lng")
                    cleaned_trip["dropoffLat"] = cleaned_trip.get("dropoff_lat")
                    cleaned_trip["dropoffLng"] = cleaned_trip.get("dropoff_lng")
                    cleaned_trip["estimatedFare"] = cleaned_trip.get("estimated_fare")

                    return cleaned_trip
        except Exception as e:
            logger.error(f"Error fetching driver active trip: {e}", exc_info=True)
            return None

    # ────────────────────────────────────────────────
    # 6. FIX METHODS FOR EXISTING TRIPS
    # ────────────────────────────────────────────────
    @staticmethod
    def fix_missing_driver_info(ride_request_id: str) -> bool:
        """Fix a specific trip with missing driver_info"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get the trip
                    cur.execute(
                        "SELECT driver_id FROM trip_service.trips WHERE ride_request_id = %s",
                        (ride_request_id,)
                    )
                    trip = cur.fetchone()
                    if not trip:
                        logger.error(f"Trip not found: {ride_request_id}")
                        return False
                    
                    driver_id = trip[0]
                    
                    # Get or create driver info
                    driver_info = TripService._get_driver_info_from_service(driver_id)
                    driver_info_json = json.dumps(driver_info)
                    
                    # Update the trip
                    cur.execute(
                        "UPDATE trip_service.trips SET driver_info = %s, updated_at = CURRENT_TIMESTAMP WHERE ride_request_id = %s",
                        (driver_info_json, ride_request_id)
                    )
                    conn.commit()
                    logger.info(f"Fixed driver_info for trip {ride_request_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to fix driver_info: {e}")
            return False

    @staticmethod
    def fix_all_missing_driver_info() -> int:
        """Fix ALL trips with missing driver_info, returns count fixed"""
        fixed_count = 0
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get all trips with NULL driver_info
                    cur.execute(
                        "SELECT ride_request_id, driver_id FROM trip_service.trips WHERE driver_info IS NULL"
                    )
                    trips = cur.fetchall()
                    
                    for ride_request_id, driver_id in trips:
                        try:
                            # Get or create driver info
                            driver_info = TripService._get_driver_info_from_service(driver_id)
                            driver_info_json = json.dumps(driver_info)
                            
                            # Update the trip
                            cur.execute(
                                "UPDATE trip_service.trips SET driver_info = %s, updated_at = CURRENT_TIMESTAMP WHERE ride_request_id = %s",
                                (driver_info_json, ride_request_id)
                            )
                            fixed_count += 1
                            logger.info(f"Fixed trip {ride_request_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to fix trip {ride_request_id}: {e}")
                            continue
                    
                    conn.commit()
                    logger.info(f"Fixed {fixed_count} trips with missing driver_info")
                    return fixed_count
                    
        except Exception as e:
            logger.error(f"Failed to fix all trips: {e}")
            return 0

    # ────────────────────────────────────────────────
    # 7. HELPER METHODS
    # ────────────────────────────────────────────────
    @staticmethod
    def _get_driver_info_from_service(driver_id: str) -> Dict[str, Any]:
        """Fetch driver info from driver_service.drivers table"""
        driver_info = {
            "name": "Unknown Driver",
            "phone": "",
            "rating": 4.8,
            "vehicle": "",
            "licensePlate": ""
        }
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT first_name, last_name, phone, rating, 
                               vehicle_make, vehicle_model, license_plate 
                        FROM driver_service.drivers 
                        WHERE id = %s
                        """,
                        (driver_id,),
                    )
                    d = cur.fetchone()
                    if d:
                        first_name = d[0] or ""
                        last_name = d[1] or ""
                        driver_name = f"{first_name} {last_name}".strip()
                        
                        vehicle_make = d[4] or ""
                        vehicle_model = d[5] or ""
                        vehicle = f"{vehicle_make} {vehicle_model}".strip()
                        
                        driver_info = {
                            "name": driver_name if driver_name else "Unknown Driver",
                            "phone": d[2] or "",
                            "rating": float(d[3]) if d[3] is not None else 4.8,
                            "vehicle": vehicle,
                            "licensePlate": d[6] or ""
                        }
        except Exception as e:
            logger.error(f"Failed to fetch driver info for {driver_id}: {e}")
        
        return driver_info

    @staticmethod
    def get_trip_by_request_id(ride_request_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ride request ID"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, status, driver_id, rider_id, driver_info
                        FROM trip_service.trips 
                        WHERE ride_request_id = %s
                        """, (ride_request_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        # Parse driver_info
                        driver_info_raw = row[4]
                        driver_info = {}
                        
                        if driver_info_raw is None:
                            driver_info = TripService._get_driver_info_from_service(row[2])
                        elif isinstance(driver_info_raw, str):
                            try:
                                driver_info = json.loads(driver_info_raw) if driver_info_raw else {}
                            except json.JSONDecodeError:
                                driver_info = {}
                        else:
                            driver_info = driver_info_raw or {}
                        
                        return {
                            "id": str(row[0]),
                            "status": row[1],
                            "driver_id": str(row[2]),
                            "rider_id": str(row[3]),
                            "driver_info": driver_info
                        }
        except Exception as e:
            logger.error(f"Error fetching trip by request ID {ride_request_id}: {e}")
        return None

    @staticmethod
    def get_ride_request_from_db(ride_request_id: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Fetch ride request details directly from rider_service. Returns (data, error_message)."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, rider_id, pickup_lat, pickup_lng, pickup_address,
                               dropoff_lat, dropoff_lng, dropoff_address,
                               vehicle_type, estimated_fare
                        FROM rider_service.ride_requests
                        WHERE id = %s
                        """,
                        (ride_request_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        data = {
                            "ride_request_id": row[0],
                            "rider_id": row[1],
                            "pickup_lat": float(row[2]),
                            "pickup_lng": float(row[3]),
                            "pickup_address": row[4],
                            "dropoff_lat": float(row[5]),
                            "dropoff_lng": float(row[6]),
                            "dropoff_address": row[7],
                            "vehicle_type": row[8],
                            "estimated_fare": float(row[9]) if row[9] else 0.0
                        }
                        return data, None
                    else:
                        return None, "Ride request not found in database (row is None)"
        except Exception as e:
            msg = f"Failed to fetch ride request {ride_request_id}: {str(e)}"
            logger.error(msg)
            return None, msg

    @staticmethod
    def get_driver_transactions(driver_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Fetch transaction history for a driver"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, trip_id, amount, transaction_type, status, metadata, created_at
                        FROM trip_service.driver_transactions
                        WHERE driver_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (driver_id, limit, offset)
                    )
                    
                    columns = [desc[0] for desc in cur.description]
                    transactions = []
                    
                    for row in cur.fetchall():
                        tx = dict(zip(columns, row))
                        # Format for JSON
                        tx['id'] = str(tx['id'])
                        tx['transaction_id'] = tx['id']
                        tx['trip_id'] = str(tx['trip_id'])
                        tx['amount'] = float(tx['amount'])
                        tx['created_at'] = tx['created_at'].isoformat()
                        
                        if isinstance(tx['metadata'], str):
                            tx['metadata'] = json.loads(tx['metadata'])
                        
                        transactions.append(tx)
                        
                    return {
                        "transactions": transactions,
                        "pagination": {
                            "total": len(transactions),
                            "limit": limit,
                            "offset": offset,
                            "has_more": len(transactions) == limit
                        }
                    }
        except Exception as e:
            logger.error(f"Error fetching transactions for driver {driver_id}: {e}")
            return {"transactions": [], "pagination": {"total": 0, "limit": limit, "offset": offset, "has_more": False}}

    @staticmethod
    def get_rider_trips(rider_id: str, status: Optional[str] = None, include_cancelled: bool = False, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Fetch trip history for a rider"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT id, ride_request_id, status, rider_id, driver_id,
                               pickup_address, dropoff_address, vehicle_type,
                               estimated_fare, actual_fare, distance_km, duration_minutes,
                               started_at, completed_at, created_at, updated_at,
                               driver_info, payment_status
                        FROM trip_service.trips 
                        WHERE rider_id = %s
                    """
                    params = [rider_id]

                    if status:
                        query += " AND status = %s"
                        params.append(status)
                    elif not include_cancelled:
                        query += " AND status != 'cancelled'"

                    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])

                    cur.execute(query, params)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()

                    trips = []
                    for row in rows:
                        trip = dict(zip(columns, row))
                        trips.append(TripService._clean_trip_dict(trip, columns))

                    # Get total count for pagination
                    count_query = "SELECT COUNT(*) FROM trip_service.trips WHERE rider_id = %s"
                    count_params = [rider_id]
                    if status:
                        count_query += " AND status = %s"
                        count_params.append(status)
                    elif not include_cancelled:
                        count_query += " AND status != 'cancelled'"
                    
                    cur.execute(count_query, count_params)
                    total = cur.fetchone()[0]

                    return {
                        "trips": trips,
                        "pagination": {
                            "total": total,
                            "limit": limit,
                            "offset": offset,
                            "has_more": offset + len(trips) < total
                        }
                    }
        except Exception as e:
            logger.error(f"Error fetching trips for rider {rider_id}: {e}")
            return {"trips": [], "pagination": {"total": 0, "limit": limit, "offset": offset, "has_more": False}}