'use client';
import { useState, useEffect } from 'react';
import PageWrapper from '@/components/layout/PageWrapper';
import HistoryTable from '@/components/history/HistoryTable';
import HistoryFilter from '@/components/history/HistoryFilter';
import Pagination from '@/components/history/Pagination';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { fetchHistory, fetchMaps } from '@/lib/api';
import styles from './page.module.css';

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const [maps, setMaps] = useState([]);
  const [mapFilter, setMapFilter] = useState('');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMaps().then(setMaps);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const offset = (page - 1) * PAGE_SIZE;
    fetchHistory({ limit: PAGE_SIZE, offset, map: mapFilter || undefined })
      .then((data) => {
        setItems(data.items ?? data);
        setTotal(data.total ?? (data.items ?? data).length);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page, mapFilter]);

  return (
    <PageWrapper>
      <h1 className={styles.pageTitle}>예측 기록</h1>
      <div className={styles.toolbar}>
        <HistoryFilter maps={maps} mapFilter={mapFilter} onMapChange={(v) => { setMapFilter(v); setPage(1); }} />
      </div>
      <div className={styles.tableSection}>
        {error && <ErrorMessage message={error} onClose={() => setError(null)} />}
        {loading ? <LoadingSpinner /> : <HistoryTable items={items} />}
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPage={setPage} />
      </div>
    </PageWrapper>
  );
}
