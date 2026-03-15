
'use client';

import React from 'react';
import { TripsResponse } from '../../../../types/driver';
import { MapPin, Calendar, Clock, Star, User } from 'lucide-react';

interface TripsContentProps {
    data: TripsResponse | null;
    isLoading: boolean;
}

export default function TripsContent({ data, isLoading }: TripsContentProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!data || !data.trips) {
        return (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-500">
                No trip history available.
            </div>
        );
    }

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-NG', {
            style: 'currency',
            currency: 'NGN',
            minimumFractionDigits: 0,
        }).format(amount);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    };

    const formatTime = (dateString: string) => {
        return new Date(dateString).toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                    <h2 className="text-lg font-bold text-gray-900">Trip History</h2>
                    <span className="text-sm text-gray-500">{data.pagination.total} Total Trips</span>
                </div>

                <div className="divide-y divide-gray-100">
                    {data.trips.map((trip) => (
                        <div key={trip.trip_id} className="p-6 hover:bg-gray-50 transition-colors">
                            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                                {/* Left: Basic Info & Path */}
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-4 text-sm">
                                        <div className="flex items-center gap-1 text-gray-500">
                                            <Calendar size={16} />
                                            <span>{formatDate(trip.created_at)}</span>
                                        </div>
                                        <div className="flex items-center gap-1 text-gray-500">
                                            <Star size={16} className="text-yellow-400 fill-yellow-400" />
                                            <span className="font-medium text-gray-900">{trip.rider.rating}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold uppercase ${trip.status === 'completed' ? 'bg-green-100 text-green-700' :
                                                    trip.status === 'cancelled' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                                                }`}>
                                                {trip.status}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="relative pl-6 space-y-4">
                                        {/* Visual Connector */}
                                        <div className="absolute left-[7px] top-[10px] bottom-[10px] w-0.5 bg-gray-200"></div>

                                        <div className="relative flex items-start gap-3">
                                            <div className="absolute left-[-23px] top-1 w-3 h-3 rounded-full border-2 border-green-500 bg-white z-10"></div>
                                            <div>
                                                <p className="text-xs text-gray-400 font-medium uppercase">Pickup</p>
                                                <p className="text-sm font-medium text-gray-900 line-clamp-1">{trip.pickup_address}</p>
                                            </div>
                                        </div>

                                        <div className="relative flex items-start gap-3">
                                            <div className="absolute left-[-23px] top-1 w-3 h-3 rounded-full border-2 border-red-500 bg-white z-10"></div>
                                            <div>
                                                <p className="text-xs text-gray-400 font-medium uppercase">Dropoff</p>
                                                <p className="text-sm font-medium text-gray-900 line-clamp-1">{trip.dropoff_address}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Right: Detailed Stats & Fare */}
                                <div className="flex flex-wrap items-center gap-6 lg:text-right">
                                    <div className="space-y-1">
                                        <p className="text-xs text-gray-400 font-medium uppercase">Passenger</p>
                                        <div className="flex items-center gap-1 lg:justify-end font-medium text-gray-900">
                                            <User size={16} className="text-gray-400" />
                                            <span>{trip.rider.name}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <p className="text-xs text-gray-400 font-medium uppercase">Duration</p>
                                        <div className="flex items-center gap-1 lg:justify-end font-medium text-gray-900">
                                            <Clock size={16} className="text-gray-400" />
                                            <span>{trip.duration_minutes} min</span>
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <p className="text-xs text-gray-400 font-medium uppercase">Earning</p>
                                        <p className="text-xl font-bold text-blue-600">
                                            {formatCurrency(trip.payment?.driver_amount || 0)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}

                    {data.trips.length === 0 && (
                        <div className="p-12 text-center text-gray-500 italic text-sm">
                            No trips recorded in history.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
