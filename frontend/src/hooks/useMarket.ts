import { useApi } from './useApi';
import { marketService } from '@/lib/api/services/market';

// Hook to get stock info
export function useStockInfo(ticker: string | null) {
  return useApi(
    () => ticker ? marketService.getStockInfo(ticker) : Promise.resolve(null),
    [ticker]
  );
}

// Hook to get stock price history
export function useStockPrice(ticker: string | null, days: number = 30) {
  return useApi(
    () => ticker ? marketService.getStockPrice(ticker, days) : Promise.resolve(null),
    [ticker, days]
  );
}

// Hook to get stock news
export function useStockNews(ticker: string | null, limit: number = 10) {
  return useApi(
    () => ticker ? marketService.getStockNews(ticker, limit) : Promise.resolve(null),
    [ticker, limit]
  );
}

// Hook to get trending stocks
export function useTrendingStocks(limit: number = 10) {
  return useApi(
    () => marketService.getTrending(limit),
    [limit]
  );
}