import { useState, useEffect, useCallback } from 'react';
import { sentimentService } from '@/lib/api/services/sentiment';
import type {
  StockSentimentResponse,
  TrendingSentimentResponse,
  StockPostsResponse,
  SentimentSummaryResponse
} from '@/types/api';

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Hook to fetch overall market sentiment summary
 */
export function useSentimentSummary(): UseApiResult<SentimentSummaryResponse> {
  const [data, setData] = useState<SentimentSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await sentimentService.getSummary();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch sentiment summary'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch trending stocks by sentiment
 */
export function useTrendingSentiment(
  limit: number = 10,
  period: '24h' | '7d' | '30d' = '24h'
): UseApiResult<TrendingSentimentResponse> {
  const [data, setData] = useState<TrendingSentimentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await sentimentService.getTrending(limit, period);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch trending sentiment'));
    } finally {
      setLoading(false);
    }
  }, [limit, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch sentiment data for a specific stock
 */
export function useStockSentiment(
  ticker: string | null,
  days: number = 7
): UseApiResult<StockSentimentResponse> {
  const [data, setData] = useState<StockSentimentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!ticker) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await sentimentService.getStockSentiment(ticker, days);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(`Failed to fetch sentiment for ${ticker}`));
    } finally {
      setLoading(false);
    }
  }, [ticker, days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch Reddit posts for a specific stock
 */
export function useStockPosts(
  ticker: string | null,
  limit: number = 20,
  sentimentFilter?: 'positive' | 'negative' | 'neutral'
): UseApiResult<StockPostsResponse> {
  const [data, setData] = useState<StockPostsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!ticker) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await sentimentService.getStockPosts(ticker, limit, sentimentFilter);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(`Failed to fetch posts for ${ticker}`));
    } finally {
      setLoading(false);
    }
  }, [ticker, limit, sentimentFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch sentiment for multiple tickers at once
 * Useful for portfolio holdings sentiment badges
 */
export function useMultipleStockSentiment(
  tickers: string[]
): {
  sentimentMap: Map<string, { label: string; score: number }>;
  loading: boolean;
  error: Error | null;
} {
  const [sentimentMap, setSentimentMap] = useState<Map<string, { label: string; score: number }>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (tickers.length === 0) {
      setSentimentMap(new Map());
      return;
    }

    const fetchAllSentiment = async () => {
      setLoading(true);
      setError(null);

      const newMap = new Map<string, { label: string; score: number }>();

      await Promise.all(
        tickers.map(async (ticker) => {
          try {
            const result = await sentimentService.getStockSentiment(ticker, 1);
            if (result && result.sentiment && result.sentiment.length > 0) {
              const latest = result.sentiment[0];
              const avgScore = latest.avg_sentiment || 0;
              let label = 'neutral';
              if (avgScore > 0.1) label = 'positive';
              else if (avgScore < -0.1) label = 'negative';

              newMap.set(ticker, { label, score: avgScore });
            }
          } catch {
            // Skip tickers that fail
          }
        })
      );

      setSentimentMap(newMap);
      setLoading(false);
    };

    fetchAllSentiment();
  }, [tickers.join(',')]); // Re-run when tickers list changes

  return { sentimentMap, loading, error };
}
