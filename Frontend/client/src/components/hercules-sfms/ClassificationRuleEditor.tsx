import React, { useEffect, useRef, useState } from 'react';
import { Trash2 } from 'lucide-react';
import {
  classificationApi,
  type ClassificationRule,
  type ClassificationRuleRequest,
} from '../../lib/api';

/**
 * Classification rule editor — Workstream A, task A6.
 *
 * Order routing used to be `prefix == "13"` -> MILLING / `"14"` -> PACKING,
 * hardcoded in the backend. A1 moved it into the `classification_rules` table;
 * this is the screen for it, so a new material prefix is a row rather than a
 * deploy.
 *
 * Lives on Material Map, under the milling version mappings, because that is
 * where an engineer already goes to change how an order is routed.
 *
 * The `plant_department` rule type is intentionally NOT offered. A1 found that
 * the system derives department from order_type, not from plant, and that
 * plant 3130 runs both departments — so such a rule would be wrong. The two
 * seeded rows are deactivated; see migrate_a1_classification_rules.py.
 */

interface Props {
  theme: string;
  isAdmin: boolean;
  onNotify: (message: string, type?: string) => void;
}

const BLANK: ClassificationRuleRequest = {
  rule_type: 'material_prefix',
  match_value: '',
  result_value: 'MILLING',
  priority: 10,
  is_active: true,
  description: '',
};

export const ClassificationRuleEditor: React.FC<Props> = ({ theme, isAdmin, onNotify }) => {
  const [rules, setRules] = useState<ClassificationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ClassificationRuleRequest>(BLANK);
  const [showForm, setShowForm] = useState(false);

  // Live preview: what would this material classify as, with the rules as they
  // stand right now?
  const [probe, setProbe] = useState('');
  const [probeResult, setProbeResult] = useState<string | null>(null);

  const light = theme === 'light';
  const cellBorder = light ? 'border-blue-200' : 'border-slate-600';
  const panel = light
    ? 'bg-white/90 border border-blue-200'
    : 'bg-slate-800/60 border border-slate-700';
  const input = `w-full px-3 py-2 rounded-md text-sm border ${
    light
      ? 'bg-white border-gray-300 text-gray-900 focus:border-blue-500'
      : 'bg-slate-900/60 border-slate-600 text-white focus:border-cyan-500'
  } focus:outline-none`;
  const label = `block text-xs font-semibold mb-1 ${light ? 'text-slate-600' : 'text-slate-300'}`;

  const load = async () => {
    setLoading(true);
    try {
      setRules(await classificationApi.getRules());
    } catch (err) {
      onNotify(`Could not load classification rules: ${(err as Error).message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced, because this runs on every keystroke and a material code is 18
  // characters — resolving as you type otherwise means 18 requests to type one
  // code. 350ms is long enough to coalesce typing and short enough to feel
  // immediate.
  const probeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (probeTimer.current) clearTimeout(probeTimer.current);
  }, []);

  const resolveProbe = async (material: string) => {
    try {
      const result = await classificationApi.resolve(material);
      setProbeResult(
        result.matched
          ? `${result.normalised} → ${result.order_type}`
          : `${result.normalised} → no rule matches`,
      );
    } catch {
      setProbeResult('could not resolve');
    }
  };

  const runProbe = (material: string) => {
    setProbe(material);
    if (probeTimer.current) clearTimeout(probeTimer.current);

    const trimmed = material.trim();
    // Fewer than two significant digits can never match a rule, so don't ask.
    if (trimmed.replace(/^0+/, '').length < 2) {
      setProbeResult(null);
      return;
    }
    probeTimer.current = setTimeout(() => resolveProbe(trimmed), 350);
  };

  const save = async () => {
    const matchValue = form.match_value.trim();
    if (!matchValue) {
      onNotify('Prefix is required', 'error');
      return;
    }
    setSaving(true);
    try {
      const saved = await classificationApi.createOrUpdateRule({
        ...form,
        match_value: matchValue,
        description: form.description?.trim() || null,
      });
      onNotify(`Rule saved: ${saved.match_value}… → ${saved.result_value}`);
      setForm(BLANK);
      setShowForm(false);
      await load();
      if (probe) runProbe(probe);
    } catch (err) {
      // The backend explains exactly why a value was rejected — show that
      // rather than a generic failure.
      onNotify((err as Error).message || 'Could not save rule', 'error');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (rule: ClassificationRule) => {
    try {
      await classificationApi.deleteRule(rule.id);
      onNotify(`Rule deleted: ${rule.match_value} → ${rule.result_value}`);
      await load();
      if (probe) runProbe(probe);
    } catch (err) {
      onNotify((err as Error).message || 'Could not delete rule', 'error');
    }
  };

  const edit = (rule: ClassificationRule) => {
    setForm({
      rule_type: rule.rule_type,
      match_value: rule.match_value,
      result_value: rule.result_value,
      priority: rule.priority,
      is_active: rule.is_active,
      description: rule.description ?? '',
    });
    setShowForm(true);
  };

  const prefixRules = rules.filter((r) => r.rule_type === 'material_prefix');
  const otherRules = rules.filter((r) => r.rule_type !== 'material_prefix');

  return (
    <div className={`rounded-xl p-4 ${panel}`}>
      <div className="flex items-start justify-between gap-4 flex-wrap mb-3">
        <div>
          <h3 className={`text-lg font-bold ${light ? 'text-slate-700' : 'text-cyan-400'}`}>
            Order Classification Rules
          </h3>
          <p className={`text-xs mt-0.5 ${light ? 'text-slate-500' : 'text-slate-400'}`}>
            Which material codes are milling, and which are packing. Matched on the
            start of the code with leading zeros removed, lowest priority first.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all hover:scale-105 disabled:opacity-50 ${
              light ? 'bg-slate-200 text-slate-700' : 'bg-slate-700 text-slate-200'
            }`}
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
          {isAdmin && (
            <button
              onClick={() => {
                setForm(BLANK);
                setShowForm((open) => !open);
              }}
              className="px-3 py-1.5 rounded-md text-xs font-semibold !text-white transition-all hover:scale-105 bg-gradient-to-r from-cyan-500 to-blue-600"
              style={{ color: 'white' }}
            >
              {showForm ? 'Cancel' : '+ Add Rule'}
            </button>
          )}
        </div>
      </div>

      {/* Preview — answers "what would this material do?" without starting an order */}
      <div className="flex items-center gap-2 flex-wrap mb-3">
        <label className={`text-xs font-semibold ${light ? 'text-slate-600' : 'text-slate-300'}`}>
          Test a material code
        </label>
        <input
          value={probe}
          onChange={(e) => runProbe(e.target.value)}
          placeholder="000000000013000099"
          className={`${input} !w-auto min-w-[16rem] font-mono`}
        />
        {probeResult && (
          <span
            className={`text-xs font-mono px-2 py-1 rounded ${
              probeResult.includes('no rule')
                ? light
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-amber-500/20 text-amber-300'
                : light
                ? 'bg-green-100 text-green-700'
                : 'bg-green-500/20 text-green-300'
            }`}
          >
            {probeResult}
          </span>
        )}
      </div>

      {isAdmin && showForm && (
        <div
          className={`rounded-lg p-3 mb-4 ${
            light ? 'bg-blue-50 border border-blue-200' : 'bg-slate-900/50 border border-slate-700'
          }`}
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className={label}>Material prefix</label>
              <input
                value={form.match_value}
                onChange={(e) => setForm({ ...form, match_value: e.target.value })}
                placeholder="15"
                className={`${input} font-mono`}
              />
              <p className={`text-[11px] mt-1 ${light ? 'text-slate-500' : 'text-slate-400'}`}>
                Digits, or <span className="font-mono">*</span> to catch everything else.
                No leading zero.
              </p>
            </div>

            <div>
              <label className={label}>Routes to</label>
              <select
                value={form.result_value}
                onChange={(e) => setForm({ ...form, result_value: e.target.value })}
                className={input}
              >
                <option value="MILLING">MILLING</option>
                <option value="PACKING">PACKING</option>
              </select>
            </div>

            <div>
              <label className={label}>Priority</label>
              <input
                type="number"
                value={form.priority ?? 10}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
                className={input}
              />
              <p className={`text-[11px] mt-1 ${light ? 'text-slate-500' : 'text-slate-400'}`}>
                Lower wins. A longer, more specific prefix needs a lower number.
              </p>
            </div>

            <div>
              <label className={label}>Description</label>
              <input
                value={form.description ?? ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="optional"
                className={input}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 mt-3">
            <label className={`flex items-center gap-2 text-xs ${light ? 'text-slate-600' : 'text-slate-300'}`}>
              <input
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              Active
            </label>
            <button
              onClick={save}
              disabled={saving}
              className="px-4 py-1.5 rounded-md text-xs font-semibold !text-white transition-all hover:scale-105 disabled:opacity-50 bg-gradient-to-r from-green-500 to-emerald-600"
              style={{ color: 'white' }}
            >
              {saving ? 'Saving…' : 'Save Rule'}
            </button>
            <span className={`text-[11px] ${light ? 'text-slate-500' : 'text-slate-400'}`}>
              Saving a prefix that already exists updates it.
            </span>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr
              className={`text-left ${
                light ? 'bg-blue-100 text-slate-700' : 'bg-slate-900/70 text-cyan-300'
              }`}
            >
              <th className={`px-3 py-2 border-r ${cellBorder}`}>Prefix</th>
              <th className={`px-3 py-2 border-r ${cellBorder}`}>Routes to</th>
              <th className={`px-3 py-2 border-r ${cellBorder}`}>Priority</th>
              <th className={`px-3 py-2 border-r ${cellBorder}`}>Active</th>
              <th className={`px-3 py-2 ${isAdmin ? `border-r ${cellBorder}` : ''}`}>Description</th>
              {isAdmin && <th className="px-3 py-2">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className={`px-3 py-4 text-center text-xs ${light ? 'text-slate-500' : 'text-slate-400'}`}>
                  Loading rules…
                </td>
              </tr>
            ) : prefixRules.length === 0 ? (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className={`px-3 py-4 text-center text-xs ${light ? 'text-amber-700' : 'text-amber-300'}`}>
                  No active classification rules. No order can be classified until
                  at least one exists.
                </td>
              </tr>
            ) : (
              prefixRules.map((rule, idx) => (
                <tr
                  key={rule.id}
                  className={`border-b ${light ? 'border-blue-100' : 'border-slate-700'} ${
                    idx % 2 === 0
                      ? light ? 'bg-white' : 'bg-slate-800/40'
                      : light ? 'bg-blue-50/50' : 'bg-slate-800/20'
                  } ${rule.is_active ? '' : 'opacity-50'}`}
                >
                  <td className={`px-3 py-2 border-r ${cellBorder} font-mono font-bold`}>
                    {rule.match_value}
                  </td>
                  <td className={`px-3 py-2 border-r ${cellBorder}`}>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        rule.result_value === 'MILLING'
                          ? light ? 'bg-blue-100 text-blue-700' : 'bg-blue-500/20 text-blue-300'
                          : light ? 'bg-purple-100 text-purple-700' : 'bg-purple-500/20 text-purple-300'
                      }`}
                    >
                      {rule.result_value}
                    </span>
                  </td>
                  <td className={`px-3 py-2 border-r ${cellBorder} font-mono`}>{rule.priority}</td>
                  <td className={`px-3 py-2 border-r ${cellBorder}`}>
                    {rule.is_active ? 'Yes' : 'No'}
                  </td>
                  <td className={`px-3 py-2 ${isAdmin ? `border-r ${cellBorder}` : ''} text-xs`}>
                    {rule.description || '-'}
                  </td>
                  {isAdmin && (
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => edit(rule)}
                          className={`px-2 py-1 rounded text-xs font-medium !text-white transition-all hover:scale-105 ${
                            light ? 'bg-blue-500 hover:bg-blue-600' : 'bg-blue-600 hover:bg-blue-700'
                          }`}
                          style={{ color: 'white' }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => remove(rule)}
                          className={`px-2 py-1 rounded text-xs font-medium text-white transition-all hover:scale-105 ${
                            light ? 'bg-red-500 hover:bg-red-600' : 'bg-red-600 hover:bg-red-700'
                          }`}
                          title="Delete rule"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {otherRules.length > 0 && (
        <p className={`text-[11px] mt-3 ${light ? 'text-slate-500' : 'text-slate-400'}`}>
          {otherRules.length} plant/department rule{otherRules.length === 1 ? '' : 's'} exist
          but are not editable here — the system derives department from the order
          type, not the plant, so they are deliberately inactive.
        </p>
      )}
    </div>
  );
};

export default ClassificationRuleEditor;
