import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useQuery } from '@tanstack/react-query';
import { uploadSession, listSessions } from '../api/client';
import { useSessionStore } from '../store/sessionStore';
import type { SessionSummary } from '../types';

export function UploadView() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [quarter, setQuarter] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const setCurrentSessionId = useSessionStore((s) => s.setCurrentSessionId);

  const { data: sessions = [], refetch } = useQuery<SessionSummary[]>({
    queryKey: ['sessions'],
    queryFn: listSessions,
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    multiple: false,
    onDrop: (accepted) => {
      if (accepted.length > 0) {
        setSelectedFile(accepted[0]);
        setError(null);
      }
    },
  });

  async function handleUpload() {
    if (!selectedFile) {
      setError('Please select an .xlsx file before uploading.');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const session = await uploadSession(selectedFile, quarter);
      await refetch();
      setCurrentSessionId(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">Planzen — Upload Plan</h1>

      <div className="bg-white rounded-lg shadow p-6 w-full max-w-md">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
          }`}
        >
          <input {...getInputProps()} />
          {selectedFile ? (
            <p className="text-green-700 font-medium">{selectedFile.name}</p>
          ) : (
            <p className="text-gray-500">
              {isDragActive ? 'Drop the file here…' : 'Drag & drop an .xlsx file, or click to select'}
            </p>
          )}
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Quarter</label>
          <select
            value={quarter}
            onChange={(e) => setQuarter(Number(e.target.value))}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            aria-label="Quarter"
          >
            {[1, 2, 3, 4].map((q) => (
              <option key={q} value={q}>Q{q}</option>
            ))}
          </select>
        </div>

        {error && (
          <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </div>

      {sessions.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 w-full max-w-md mt-6">
          <h2 className="text-lg font-semibold text-gray-700 mb-3">Existing Sessions</h2>
          <ul className="space-y-2">
            {sessions.map((s) => (
              <li key={s.session_id} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">
                  {s.filename} <span className="text-gray-400">(Q{s.quarter})</span>
                </span>
                <button
                  onClick={() => setCurrentSessionId(s.session_id)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Load
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
