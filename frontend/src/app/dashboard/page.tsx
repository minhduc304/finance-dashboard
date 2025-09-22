'use client';

import { PortfolioOverview } from '@/components/dashboard/PortfolioOverview';

export default function DashboardPage() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Finance Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to your finance dashboard
          </p>
        </div>
      </div>

      <PortfolioOverview />

      {/* Add more dashboard components here */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Placeholder for future components */}
        <div className="col-span-full">
          <p className="text-muted-foreground text-center py-8">
            More dashboard features coming soon...
          </p>
        </div>
      </div>
    </div>
  );
}