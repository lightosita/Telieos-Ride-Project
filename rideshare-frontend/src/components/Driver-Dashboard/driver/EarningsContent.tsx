
'use client';

import React from 'react';
import { EarningsData } from '../../../../types/driver';
import { Wallet, TrendingUp, History, DollarSign } from 'lucide-react';

interface EarningsContentProps {
    data: EarningsData | null;
    isLoading: boolean;
}

export default function EarningsContent({ data, isLoading }: EarningsContentProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-500">
                No earnings data available.
            </div>
        );
    }

    const { summary, transactions } = data;
    const { statistics, account } = summary;

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
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-6">
            {/* Account Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-500 text-sm font-medium">Available Balance</span>
                        <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                            <Wallet size={20} />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{formatCurrency(account.current_balance)}</p>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-500 text-sm font-medium">Total Lifetime Earnings</span>
                        <div className="p-2 bg-green-50 rounded-lg text-green-600">
                            <TrendingUp size={20} />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{formatCurrency(account.total_earnings)}</p>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-500 text-sm font-medium">Total Trips</span>
                        <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
                            <History size={20} />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{statistics.total_trips}</p>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-500 text-sm font-medium">Average per Trip</span>
                        <div className="p-2 bg-orange-50 rounded-lg text-orange-600">
                            <DollarSign size={20} />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{formatCurrency(statistics.average_driver_earned || 0)}</p>
                </div>
            </div>

            {/* Transaction History */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-6 border-b border-gray-100">
                    <h2 className="text-lg font-bold text-gray-900">Recent Transactions</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider">
                            <tr>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Trip ID</th>
                                <th className="px-6 py-4">Amount</th>
                                <th className="px-6 py-4">Total Fare</th>
                                <th className="px-6 py-4">Date</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {transactions?.transactions?.map((tx, index) => (
                                <tr key={tx.transaction_id || tx.id || `tx-${index}`} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium uppercase ${tx.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                                            }`}>
                                            {tx.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                                        #{tx.trip_id?.slice(-8)}
                                    </td>
                                    <td className="px-6 py-4 text-sm font-bold text-green-600">
                                        +{formatCurrency(tx.amount)}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {formatCurrency(tx.metadata?.total_fare || 0)}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {tx.created_at ? formatDate(tx.created_at) : 'N/A'}
                                    </td>
                                </tr>
                            ))}
                            {(!transactions?.transactions || transactions.transactions.length === 0) && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500 italic">
                                        No transactions found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
