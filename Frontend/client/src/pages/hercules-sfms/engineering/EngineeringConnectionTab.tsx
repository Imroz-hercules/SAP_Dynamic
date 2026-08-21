import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Lock, RefreshCw, Save, Wifi } from 'lucide-react';
import { useTheme } from '../../../contexts/ThemeContext';
import { getApiUrl, apiFetch } from '../../../lib/apiConfig';

/**
 * Plant connection settings (Workstream A8).
 * Lives on Engineering as the Connection tab.
 */

interface SettingRow {
  key: string;
  label: string;
  group: string;
  kind: 'string' | 'integer' | 'float' | 'boolean' | 'url';
  secret: boolean;
  editable: boolean;
  help: string;
  value: string | number | boolean;
  source: 'database' | 'env' | 'default' | 'unknown';
  env_var: string | null;
}

interface SettingsGroup {
  name: string;
  settings: SettingRow[];
}

interface Excluded {
  name: string;
  reason: string;
}

interface TestResult {
  ok: boolean;
  url: string;
  status_code?: number;
  elapsed_ms?: number;
  mock_mode: boolean;
  error?: string;
  hint?: string;
}

export const EngineeringConnectionTab: React.FC = () => {
  const { theme } = useTheme();
  const light = theme === 'light';

  const [groups, setGroups] = useState<SettingsGroup[]>([]);
  const [excluded, setExcluded] = useState<Excluded[]>([]);
  const [missing, setMissing] = useState<string[]>([]);
  const [edits, setEdits] = useState<Record<string, string | number | boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [notice, setNotice] = useState<{ message: string; kind: 'success' | 'error' } | null>(null);

  const panel = light
    ? 'bg-white/90 border border-blue-200'
    : 'bg-slate-800/60 border border-slate-700';
  const inputClass = `w-full px-3 py-2 rounded-md text-sm border ${
    light
      ? 'bg-white border-gray-300 text-gray-900 focus:border-blue-500'
      : 'bg-slate-900/60 border-slate-600 text-white focus:border-cyan-500'
  } focus:outline-none disabled:opacity-50`;

  const flash = (message: string, kind: 'success' | 'error' = 'success') => {
    setNotice({ message, kind });
    setTimeout(() => setNotice(null), 5000);
  };

  const regroup = (rows: SettingRow[]): SettingsGroup[] => {
    const out: SettingsGroup[] = [];
    rows.forEach((row) => {
      let group = out.find((g) => g.name === row.group);
      if (!group) {
        group = { name: row.group, settings: [] };
        out.push(group);
      }
      group.settings.push(row);
    });
    return out;
  };

  const load = async () => {
    setLoading(true);
    try {
      const response = await apiFetch(getApiUrl('/api/engineering/settings'));
      if (!response.ok) {
        throw new Error(
          response.status === 403
            ? 'Administrator access required'
            : `HTTP ${response.status}`,
        );
      }
      const data = await response.json();
      setGroups(data.groups || []);
      setExcluded(data.excluded || []);
      setMissing(data.missing_required || []);
      setEdits({});
    } catch (err) {
      flash(`Could not load settings: ${(err as Error).message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async () => {
    if (Object.keys(edits).length === 0) {
      flash('Nothing changed', 'error');
      return;
    }
    setSaving(true);
    try {
      const response = await apiFetch(getApiUrl('/api/engineering/settings'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: edits }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);

      setGroups(regroup(data.settings || []));
      setMissing(data.missing_required || []);
      setEdits({});

      const saved = data.saved || [];
      const skipped = (data.skipped || []).filter(
        (s: { reason: string }) => s.reason !== 'unchanged',
      );
      if (skipped.length) {
        flash(
          `Saved ${saved.length}. Not saved: ${skipped
            .map((s: { key: string; reason: string }) => `${s.key} (${s.reason})`)
            .join(', ')}`,
          'error',
        );
      } else {
        flash(`Saved ${saved.length} setting${saved.length === 1 ? '' : 's'}. In effect now — no restart.`);
      }
    } catch (err) {
      flash(`Could not save: ${(err as Error).message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await apiFetch(getApiUrl('/api/engineering/test-sap'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      setTestResult(await response.json());
    } catch (err) {
      setTestResult({
        ok: false,
        url: '-',
        mock_mode: false,
        error: (err as Error).message,
      });
    } finally {
      setTesting(false);
    }
  };

  const sourceBadge = (source: SettingRow['source']) => {
    const styles: Record<string, string> = {
      database: light ? 'bg-green-100 text-green-700' : 'bg-green-500/20 text-green-300',
      env: light ? 'bg-blue-100 text-blue-700' : 'bg-blue-500/20 text-blue-300',
      default: light ? 'bg-slate-200 text-slate-600' : 'bg-slate-700 text-slate-300',
      unknown: light ? 'bg-red-100 text-red-700' : 'bg-red-500/20 text-red-300',
    };
    const titles: Record<string, string> = {
      database: 'Saved on this screen',
      env: 'Inherited from .env on the server',
      default: 'Built-in default — nothing has ever set this',
      unknown: 'Unknown',
    };
    return (
      <span
        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${styles[source]}`}
        title={titles[source]}
      >
        {source}
      </span>
    );
  };

  const field = (row: SettingRow) => {
    const current = row.key in edits ? edits[row.key] : row.value;
    const dirty = row.key in edits;

    return (
      <div key={row.key} className="space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <label className={`text-xs font-semibold ${light ? 'text-slate-700' : 'text-cyan-300'}`}>
            {row.label}
          </label>
          {sourceBadge(row.source)}
          {!row.editable && (
            <span className={`flex items-center gap-1 text-[10px] ${light ? 'text-slate-500' : 'text-slate-400'}`}>
              <Lock className="w-2.5 h-2.5" /> read-only
            </span>
          )}
          {dirty && (
            <span className={`text-[10px] font-semibold ${light ? 'text-amber-600' : 'text-amber-400'}`}>
              unsaved
            </span>
          )}
        </div>

        {row.kind === 'boolean' ? (
          <label className={`flex items-center gap-2 text-sm ${light ? 'text-slate-700' : 'text-slate-200'}`}>
            <input
              type="checkbox"
              disabled={!row.editable}
              checked={Boolean(current)}
              onChange={(e) => setEdits({ ...edits, [row.key]: e.target.checked })}
            />
            {Boolean(current) ? 'Enabled' : 'Disabled'}
          </label>
        ) : (
          <input
            type={row.kind === 'integer' || row.kind === 'float' ? 'number' : 'text'}
            step={row.kind === 'float' ? '0.1' : undefined}
            disabled={!row.editable}
            value={String(current ?? '')}
            placeholder={row.secret ? 'unchanged' : ''}
            onChange={(e) =>
              setEdits({
                ...edits,
                [row.key]:
                  row.kind === 'integer' || row.kind === 'float'
                    ? Number(e.target.value)
                    : e.target.value,
              })
            }
            className={`${inputClass} ${row.secret ? 'font-mono' : ''}`}
          />
        )}

        {row.help && (
          <p className={`text-[11px] leading-snug ${light ? 'text-slate-500' : 'text-slate-400'}`}>
            {row.help}
            {row.env_var && (
              <span className="font-mono opacity-70"> · {row.env_var}</span>
            )}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {notice && (
        <div
          className={`px-3 py-2 rounded-md text-sm ${
            notice.kind === 'success'
              ? light
                ? 'bg-green-100 border border-green-500 text-green-700'
                : 'bg-green-500/20 border border-green-500 text-green-300'
              : light
              ? 'bg-red-100 border border-red-500 text-red-700'
              : 'bg-red-500/20 border border-red-500 text-red-300'
          }`}
        >
          {notice.message}
        </div>
      )}

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 className={`text-sm font-semibold ${light ? 'text-slate-800' : 'text-white'}`}>
            SAP &amp; SQL Server connection
          </h3>
          <p className={`text-xs mt-1 max-w-2xl ${light ? 'text-slate-500' : 'text-slate-400'}`}>
            Saved values take effect on the next call — no restart. Unsaved fields fall back to
            <span className="font-mono"> .env</span>, then to a built-in default.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all hover:scale-105 disabled:opacity-50 ${
              light ? 'bg-slate-200 text-slate-700' : 'bg-slate-700 text-slate-200'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Reload
          </button>
          <button
            onClick={test}
            disabled={testing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold !text-white transition-all hover:scale-105 disabled:opacity-50 bg-gradient-to-r from-cyan-500 to-blue-600"
            style={{ color: 'white' }}
          >
            <Wifi className={`w-3.5 h-3.5 ${testing ? 'animate-pulse' : ''}`} />
            {testing ? 'Testing…' : 'Test SAP'}
          </button>
          <button
            onClick={save}
            disabled={saving || Object.keys(edits).length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-xs font-semibold !text-white transition-all hover:scale-105 disabled:opacity-40 bg-gradient-to-r from-green-500 to-emerald-600"
            style={{ color: 'white' }}
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? 'Saving…' : `Save${Object.keys(edits).length ? ` (${Object.keys(edits).length})` : ''}`}
          </button>
        </div>
      </div>

      {missing.length > 0 && (
        <div
          className={`rounded-lg p-3 flex items-start gap-2 ${
            light ? 'bg-red-50 border border-red-300' : 'bg-red-500/10 border border-red-500/40'
          }`}
        >
          <AlertTriangle className={`w-4 h-4 mt-0.5 ${light ? 'text-red-600' : 'text-red-400'}`} />
          <div className={`text-xs ${light ? 'text-red-700' : 'text-red-300'}`}>
            <strong>Required settings are missing:</strong> {missing.join(', ')}.
          </div>
        </div>
      )}

      {testResult && (
        <div
          className={`rounded-lg p-3 ${
            testResult.ok
              ? light ? 'bg-green-50 border border-green-300' : 'bg-green-500/10 border border-green-500/40'
              : light ? 'bg-amber-50 border border-amber-300' : 'bg-amber-500/10 border border-amber-500/40'
          }`}
        >
          <div className="flex items-start gap-2">
            {testResult.ok ? (
              <CheckCircle2 className={`w-4 h-4 mt-0.5 ${light ? 'text-green-600' : 'text-green-400'}`} />
            ) : (
              <AlertTriangle className={`w-4 h-4 mt-0.5 ${light ? 'text-amber-600' : 'text-amber-400'}`} />
            )}
            <div className={`text-xs space-y-0.5 ${light ? 'text-slate-700' : 'text-slate-200'}`}>
              <div className="font-mono break-all">{testResult.url}</div>
              <div>
                {testResult.ok
                  ? `HTTP ${testResult.status_code} in ${testResult.elapsed_ms} ms`
                  : testResult.error}
                {testResult.mock_mode && ' · mock SAP mode is on'}
              </div>
              {testResult.hint && <div className="opacity-80">{testResult.hint}</div>}
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className={`py-10 text-center text-sm ${light ? 'text-slate-500' : 'text-slate-400'}`}>
          Loading settings…
        </div>
      ) : (
        groups.map((group) => (
          <div key={group.name} className={`rounded-xl p-4 ${panel}`}>
            <h3 className={`text-sm font-bold mb-3 ${light ? 'text-slate-700' : 'text-cyan-400'}`}>
              {group.name}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {group.settings.map(field)}
            </div>
          </div>
        ))
      )}

      {excluded.length > 0 && (
        <div className={`rounded-xl p-4 ${panel}`}>
          <h3 className={`text-sm font-bold mb-2 ${light ? 'text-slate-700' : 'text-cyan-400'}`}>
            Deliberately not on this page
          </h3>
          <ul className="space-y-2">
            {excluded.map((item) => (
              <li key={item.name} className="text-xs">
                <span className={`font-mono font-semibold ${light ? 'text-slate-700' : 'text-slate-200'}`}>
                  {item.name}
                </span>
                <span className={light ? 'text-slate-500' : 'text-slate-400'}> — {item.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
