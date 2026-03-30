import { useState, useEffect, useCallback } from 'react';
import { getConcursos } from '../services/api';
import type { Concurso, ConcursoFilters, PaginatedResponse } from '../services/api';

const DEFAULT_PAGE_SIZE = 20;

export function useConcursos(filters: ConcursoFilters = {}) {
  const [data, setData] = useState<PaginatedResponse<Concurso> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const fetch = useCallback(async (currentPage: number, currentFilters: ConcursoFilters) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getConcursos({ ...currentFilters, page: currentPage, page_size: DEFAULT_PAGE_SIZE });
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar concursos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setPage(1);
    fetch(1, filters);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  const goToPage = useCallback((newPage: number) => {
    setPage(newPage);
    fetch(newPage, filters);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters), fetch]);

  const refresh = useCallback(() => {
    fetch(page, filters);
  }, [page, filters, fetch]);

  return {
    concursos: data?.items ?? [],
    total: data?.total ?? 0,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: data ? Math.ceil(data.total / DEFAULT_PAGE_SIZE) : 0,
    loading,
    error,
    goToPage,
    refresh,
  };
}
