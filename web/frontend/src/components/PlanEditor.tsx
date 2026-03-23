import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSessionStore } from '../store/sessionStore';
import { getSession, computeAllocation } from '../api/client';
import { CapacityEditor } from './CapacityEditor';
import { EpicsTable } from './EpicsTable';
import { AllocationPreview } from './AllocationPreview';
import { ExportBar } from './ExportBar';
import type { ComputeResponse } from '../types';

export function PlanEditor() {
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const setCurrentSessionId = useSessionStore((s) => s.setCurrentSessionId);
  const queryClient = useQueryClient();
  const [computeResult, setComputeResult] = useState<ComputeResponse | null>(null);
  const [isComputing, setIsComputing] = useState(false);

  const { data: session, isLoading, isError } = useQuery({
    queryKey: ['session', currentSessionId],
    queryFn: () => getSession(currentSessionId!),
    enabled: !!currentSessionId,
  });

  const recompute = useCallback(async () => {
    if (!currentSessionId) return;
    setIsComputing(true);
    try {
      const result = await computeAllocation(currentSessionId);
      setComputeResult(result);
    } finally {
      setIsComputing(false);
    }
  }, [currentSessionId]);

  useEffect(() => {
    if (session) recompute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.session_id]);

  function handleCapacityChanged() {
    queryClient.invalidateQueries({ queryKey: ['session', currentSessionId] });
    recompute();
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" role="status" aria-label="Loading" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-red-600">Failed to load session.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{session.filename}</h1>
            <p className="text-sm text-gray-500 mt-1">Quarter {session.quarter}</p>
          </div>
          <div className="flex items-center gap-3">
            {isComputing && (
              <span className="flex items-center gap-1.5 text-sm text-gray-500">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                Computing…
              </span>
            )}
            <ExportBar
              sessionId={session.session_id}
              filename={session.filename}
              quarter={session.quarter}
            />
            <button
              type="button"
              onClick={() => setCurrentSessionId(null)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              ← Back
            </button>
          </div>
        </div>

        {/* Capacity Editor */}
        <CapacityEditor
          sessionId={session.session_id}
          capacity={session.capacity}
          onCapacityChanged={handleCapacityChanged}
        />

        {/* Epics Table */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Epics</h2>
          <EpicsTable
            sessionId={session.session_id}
            epics={session.epics}
            onEpicsChanged={recompute}
          />
        </div>

        {/* Allocation Preview */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Allocation Preview</h2>
          <AllocationPreview
            sessionId={session.session_id}
            computeResponse={computeResult}
            onOverrideChanged={recompute}
          />
        </div>
      </div>
    </div>
  );
}
