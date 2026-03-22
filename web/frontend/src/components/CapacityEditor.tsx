import { useState, useEffect, useRef } from 'react';
import type { CapacityConfig } from '../types';
import { updateCapacity } from '../api/client';

interface CapacityEditorProps {
  sessionId: string;
  capacity: CapacityConfig;
  onCapacityChanged: () => void;
}

export function CapacityEditor({ sessionId, capacity, onCapacityChanged }: CapacityEditorProps) {
  const [values, setValues] = useState<CapacityConfig>(capacity);
  const [weeklyOpen, setWeeklyOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    setValues(capacity);
  }, [capacity]);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      await updateCapacity(sessionId, values);
      onCapacityChanged();
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [values]);

  function handleChange(field: keyof CapacityConfig, raw: string) {
    const val = parseFloat(raw);
    if (!isNaN(val)) {
      setValues((prev) => ({ ...prev, [field]: val }));
    }
  }

  const hasWeeklyOverrides =
    Object.keys(values.eng_bruto_by_week ?? {}).length > 0 ||
    Object.keys(values.eng_absence_by_week ?? {}).length > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Capacity Configuration</h2>

      <div className="grid grid-cols-2 gap-8">
        {/* Engineer column */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Engineer</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Bruto Capacity <span className="text-gray-400 font-normal">FTE</span>
            </label>
            <input
              type="number"
              step="0.1"
              value={values.eng_bruto}
              aria-label="eng_bruto"
              onChange={(e) => handleChange('eng_bruto', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Absence <span className="text-gray-400 font-normal">PW/week</span>
            </label>
            <input
              type="number"
              step="0.1"
              value={values.eng_absence}
              aria-label="eng_absence"
              onChange={(e) => handleChange('eng_absence', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Management column */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Management</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Bruto Capacity <span className="text-gray-400 font-normal">FTE</span>
            </label>
            <input
              type="number"
              step="0.1"
              value={values.mgmt_capacity}
              aria-label="mgmt_capacity"
              onChange={(e) => handleChange('mgmt_capacity', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Absence <span className="text-gray-400 font-normal">PW/week</span>
            </label>
            <input
              type="number"
              step="0.1"
              value={values.mgmt_absence}
              aria-label="mgmt_absence"
              onChange={(e) => handleChange('mgmt_absence', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {hasWeeklyOverrides && (
        <div className="mt-6">
          <button
            type="button"
            onClick={() => setWeeklyOpen((o) => !o)}
            className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            <span>{weeklyOpen ? '▾' : '▸'}</span>
            Per-week overrides
          </button>

          {weeklyOpen && (
            <div className="mt-3 rounded-md border border-gray-100 bg-gray-50 p-4 space-y-4">
              {Object.keys(values.eng_bruto_by_week ?? {}).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Engineer Bruto (FTE)
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(values.eng_bruto_by_week).map(([week, val]) => (
                      <div key={week} className="text-xs text-gray-700">
                        <span className="font-medium">{week}:</span> {val}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(values.eng_absence_by_week ?? {}).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Engineer Absence (PW/week)
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(values.eng_absence_by_week).map(([week, val]) => (
                      <div key={week} className="text-xs text-gray-700">
                        <span className="font-medium">{week}:</span> {val}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
