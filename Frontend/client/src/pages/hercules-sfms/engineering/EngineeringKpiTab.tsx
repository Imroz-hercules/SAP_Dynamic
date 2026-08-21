import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, Save, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  kpiConfigApi,
  type KpiDefinition,
  type KpiDefinitionRequest,
} from '@/lib/api';

const DEPARTMENTS: KpiDefinition['department'][] = ['MILLING', 'PACKING'];

const emptyForm = (): KpiDefinitionRequest => ({
  kpi_key: '',
  display_name: '',
  department: 'MILLING',
  target_column: '',
  max_value: null,
  unit: '',
  is_active: true,
  sort_order: 0,
});

export const EngineeringKpiTab: React.FC = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState<KpiDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState<string>('ALL');
  const [form, setForm] = useState<KpiDefinitionRequest>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await kpiConfigApi.getDefinitions(
        filter === 'ALL' ? undefined : filter,
      );
      setRows(Array.isArray(data) ? data : []);
    } catch (err: any) {
      toast({
        title: 'Failed to load KPI definitions',
        description: err?.message || 'Request failed',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const startEdit = (row: KpiDefinition) => {
    setEditingId(row.id);
    setForm({
      kpi_key: row.kpi_key,
      display_name: row.display_name,
      department: row.department,
      target_column: row.target_column || '',
      max_value: row.max_value ?? null,
      unit: row.unit || '',
      is_active: row.is_active,
      sort_order: row.sort_order,
    });
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(emptyForm());
  };

  const save = async () => {
    if (!form.kpi_key.trim() || !form.display_name.trim()) {
      toast({ title: 'KPI key and display name are required', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      await kpiConfigApi.upsertDefinition(form);
      toast({ title: editingId ? 'KPI updated' : 'KPI saved' });
      resetForm();
      await load();
    } catch (err: any) {
      toast({
        title: 'Save failed',
        description: err?.message || 'Request failed',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number, key: string) => {
    if (!window.confirm(`Delete KPI "${key}"?`)) return;
    try {
      await kpiConfigApi.deleteDefinition(id);
      toast({ title: 'KPI deleted' });
      if (editingId === id) resetForm();
      await load();
    } catch (err: any) {
      toast({
        title: 'Delete failed',
        description: err?.message || 'Request failed',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-white light:text-gray-900 font-semibold">KPI Limits &amp; Definitions</h3>
          <p className="text-slate-400 light:text-gray-600 text-xs">
            Targets and display metadata for milling and packing KPIs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-8 rounded-md border border-slate-600 light:border-gray-300 bg-slate-700 light:bg-white text-white light:text-gray-900 text-xs px-2"
          >
            <option value="ALL">All departments</option>
            {DEPARTMENTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg p-4 border border-slate-600 light:border-gray-200 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-white light:text-gray-900 text-sm font-medium">
            {editingId ? `Edit KPI #${editingId}` : 'Add / upsert KPI'}
          </h4>
          {editingId && (
            <Button size="sm" variant="ghost" onClick={resetForm}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              New
            </Button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">KPI key</label>
            <Input
              value={form.kpi_key}
              onChange={(e) => setForm({ ...form, kpi_key: e.target.value })}
              placeholder="extraction_rate"
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Display name</label>
            <Input
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Department</label>
            <select
              value={form.department}
              onChange={(e) =>
                setForm({ ...form, department: e.target.value as KpiDefinition['department'] })
              }
              className="w-full h-8 rounded-md border border-slate-600 light:border-gray-300 bg-slate-700 light:bg-white text-white light:text-gray-900 text-sm px-2"
            >
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Target column</label>
            <Input
              value={form.target_column || ''}
              onChange={(e) => setForm({ ...form, target_column: e.target.value })}
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Max / target</label>
            <Input
              type="number"
              value={form.max_value ?? ''}
              onChange={(e) =>
                setForm({
                  ...form,
                  max_value: e.target.value === '' ? null : Number(e.target.value),
                })
              }
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Unit</label>
            <Input
              value={form.unit || ''}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Sort order</label>
            <Input
              type="number"
              value={form.sort_order ?? 0}
              onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) || 0 })}
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-300 light:text-gray-700">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
          <Button size="sm" onClick={save} disabled={saving} className="ml-auto">
            <Save className="h-3.5 w-3.5 mr-1" />
            {saving ? 'Saving…' : 'Save KPI'}
          </Button>
        </div>
      </div>

      <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg border border-slate-600 light:border-gray-200 overflow-hidden">
        <div className="overflow-x-auto max-h-[420px]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-800 light:bg-gray-100 text-left text-xs text-slate-300 light:text-gray-600">
              <tr>
                <th className="px-3 py-2">Key</th>
                <th className="px-3 py-2">Department</th>
                <th className="px-3 py-2">Max</th>
                <th className="px-3 py-2">Unit</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">Loading…</td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">No KPI definitions</td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-t border-slate-600/40 light:border-gray-200 hover:bg-slate-600/20 light:hover:bg-white/60"
                  >
                    <td className="px-3 py-2 text-white light:text-gray-900">
                      <span className="font-medium">{row.display_name}</span>
                      <span className="block text-xs font-mono text-slate-500">{row.kpi_key}</span>
                    </td>
                    <td className="px-3 py-2 text-slate-300 light:text-gray-700">{row.department}</td>
                    <td className="px-3 py-2 font-mono text-slate-300 light:text-gray-700">
                      {row.max_value ?? '—'}
                    </td>
                    <td className="px-3 py-2 text-slate-300 light:text-gray-700">{row.unit || '—'}</td>
                    <td className="px-3 py-2">
                      <span className={row.is_active ? 'text-green-400' : 'text-slate-500'}>
                        {row.is_active ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1 justify-end">
                        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => startEdit(row)}>
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-red-400"
                          onClick={() => remove(row.id, row.kpi_key)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
