'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ActiveRide from '@/src/components/Driver-Dashboard/activeTrip';
import { TripData } from '@/types/trip';



export default function ActiveTripPage() {
  const router = useRouter();
  const { token, user } = useAuthStore();
  const [trip, setTrip] = useState<TripData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_DRIVER_SERVICE_URL || "http://localhost:3003";

  const fetchActiveTrip = useCallback(async () => {
    if (!token || !user?.id) {
      router.replace('/driver/dashboard');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/v1/drivers/active-trip`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const body = await res.json();

      if (res.ok && body?.success) {
        if (body.data) {
          console.log('Driver service response:', body.data);
          setTrip(body.data);
        } else {
          setError('No active trip found.');
          router.push('/driver/dashboard');
        }
      } else {
        console.error('Driver service error:', body);
        setError('Could not load active trip.');
        router.push('/driver/dashboard');
      }
    } catch (err: any) {
      setError('Could not load active trip.');
    } finally {
      setLoading(false);
    }
  }, [token, user?.id, router, API_BASE]);

  useEffect(() => {
    fetchActiveTrip();
  }, [fetchActiveTrip]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-indigo-600 mx-auto"></div>
          <p className="mt-6 text-lg text-gray-400">Loading trip details...</p>
        </div>
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
        <p>{error || 'Trip not found'}</p>
      </div>
    );
  }

  const tripData = trip as any;

  return (
    <ActiveRide
      rideRequestId={tripData.ride_request_id || ''}
      status={tripData.status as any}
      riderInfo={{
        name: tripData.rider?.name || 'Rider',
        phone: tripData.rider?.phone || 'No phone provided',
        rating: tripData.rider?.rating || 5.0,
        id: '',
      }}
      pickupLocation={{
        lat: 6.5244, 
        lng: 3.3792,
        address: tripData.pickup_address || '',
      }}
      dropoffLocation={{
        lat: 6.5244, 
        lng: 3.3792,
        address: tripData.dropoff_address || '',
      }}
      fareEstimate={tripData.estimated_fare || 0}
      userId={user?.id || ''}
      liveDriverLocation={null}
    />
  );
}