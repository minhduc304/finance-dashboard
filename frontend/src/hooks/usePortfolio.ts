import { useApi, useLazyApi } from './useApi';
import { portfolioService } from '@/lib/api/services/portfolio';
import type { PortfolioSummary, Holding, Transaction } from '@/types/api';

// Hook to get all portfolios
export function usePortfolios() {
  return useApi(() => portfolioService.getAllPortfolios());
}

// Hook to get portfolio details
export function usePortfolioDetails(portfolioId: number | null) {
  return useApi(
    () => portfolioId ? portfolioService.getPortfolioDetails(portfolioId) : Promise.resolve(null),
    [portfolioId]
  );
}

// Hook to get holdings
export function useHoldings(portfolioId: number | null) {
  return useApi(
    () => portfolioId ? portfolioService.getHoldings(portfolioId) : Promise.resolve([]),
    [portfolioId]
  );
}

// Hook to get transactions
export function useTransactions(portfolioId: number | null, limit?: number) {
  return useApi(
    () => portfolioId ? portfolioService.getTransactions(portfolioId, limit) : Promise.resolve([]),
    [portfolioId, limit]
  );
}

// Hook to get performance
export function usePortfolioPerformance(portfolioId: number | null, days: number = 30) {
  return useApi(
    () => portfolioId ? portfolioService.getPerformance(portfolioId, days) : Promise.resolve(null),
    [portfolioId, days]
  );
}

// Hook for lazy portfolio update
export function useUpdatePortfolio() {
  return useLazyApi<any>((portfolioId: number) =>
    portfolioService.updatePortfolio(portfolioId)
  );
}

// Hook for lazy transaction addition
export function useAddTransaction() {
  return useLazyApi<Transaction>((
    portfolioId: number,
    transaction: {
      symbol: string;
      type: 'buy' | 'sell';
      quantity: number;
      price: number;
      date: string;
    }
  ) => portfolioService.addTransaction(portfolioId, transaction));
}