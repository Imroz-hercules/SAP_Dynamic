import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, Save, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  scadaConfigApi,
  type ScadaTag,
  type ScadaTagRequest,
} from '@/lib/api';

const CATEGORIES: ScadaTag['category'][] = ['INPUT', 'MILLING', 'WATER', 'PACKING', 'DAMAGED'];
const READING_TYPES: ScadaTag['reading_type'][] = ['hi_lo', 'single', 'average'];

const emptyForm = (): ScadaTagRequest => ({
  tag: '',
  category: 'MILLING',
  reading_type: 'hi_lo',
  display_name: '',
  source_column: '',
  unit: '',
  is_pollable: true,
  is_active: true,
  emulator_seed: 0,
  sort_order: 0,
});

export const EngineeringTagsTab: React.FC = () => {
  const { toast } = useToast();
  const [tags, setTags] = useState<ScadaTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState<string>('ALL');
  const [form, setForm] = useState<ScadaTagRequest>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await scadaConfigApi.getTags(filter === 'ALL' ? undefined : filter);
      setTags(Array.isArray(data) ? data : []);
    } catch (err: any) {
      toast({
        title: 'Failed to load SCADA tags',
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

  const startEdit = (tag: ScadaTag) => {
    setEditingId(tag.id);
    setForm({
      tag: tag.tag,
      category: tag.category,
      reading_type: tag.reading_type,
      display_name: tag.display_name || '',
      source_column: tag.source_column || '',
      unit: tag.unit || '',
      rollover_max: tag.rollover_max ?? undefined,
      is_pollable: tag.is_pollable,
      is_active: tag.is_active,
      emulator_seed: tag.emulator_seed,
      sort_order: tag.sort_order,
    });
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(emptyForm());
  };

  const save = async () => {
    if (!form.tag.trim()) {
      toast({ title: 'Tag name is required', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      await scadaConfigApi.createOrUpdateTag(form);
      toast({ title: editingId ? 'Tag updated' : 'Tag saved' });
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

  const remove = async (id: number, name: string) => {
    if (!window.confirm(`Delete SCADA tag "${name}"?`)) return;
    try {
      await scadaConfigApi.deleteTag(id);
      toast({ title: 'Tag deleted' });
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
          <h3 className="text-white light:text-gray-900 font-semibold">SCADA Tags</h3>
          <p className="text-slate-400 light:text-gray-600 text-xs">
            Registry used by the emulator, live monitor, and KPI calculations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-8 rounded-md border border-slate-600 light:border-gray-300 bg-slate-700 light:bg-white text-white light:text-gray-900 text-xs px-2"
          >
            <option value="ALL">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
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
            {editingId ? `Edit tag #${editingId}` : 'Add / upsert tag'}
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
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Tag</label>
            <Input
              value={form.tag}
              onChange={(e) => setForm({ ...form, tag: e.target.value })}
              placeholder="WG101"
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Display name</label>
            <Input
              value={form.display_name || ''}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="bg-slate-700 light:bg-white border-slate-600 light:border-gray-300 text-white light:text-gray-900 h-8 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Category</label>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value as ScadaTag['category'] })}
              className="w-full h-8 rounded-md border border-slate-600 light:border-gray-300 bg-slate-700 light:bg-white text-white light:text-gray-900 text-sm px-2"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Reading type</label>
            <select
              value={form.reading_type}
              onChange={(e) => setForm({ ...form, reading_type: e.target.value as ScadaTag['reading_type'] })}
              className="w-full h-8 rounded-md border border-slate-600 light:border-gray-300 bg-slate-700 light:bg-white text-white light:text-gray-900 text-sm px-2"
            >
              {READING_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Source column</label>
            <Input
              value={form.source_column || ''}
              onChange={(e) => setForm({ ...form, source_column: e.target.value })}
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
            <label className="text-xs text-slate-400 light:text-gray-600 block mb-1">Emulator seed</label>
            <Input
              type="number"
              value={form.emulator_seed ?? 0}
              onChange={(e) => setForm({ ...form, emulator_seed: Number(e.target.value) || 0 })}
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
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!form.is_pollable}
              onChange={(e) => setForm({ ...form, is_pollable: e.target.checked })}
            />
            Pollable
          </label>
          <Button size="sm" onClick={save} disabled={saving} className="ml-auto">
            <Save className="h-3.5 w-3.5 mr-1" />
            {saving ? 'Saving…' : 'Save tag'}
          </Button>
        </div>
      </div>

      <div className="bg-slate-700/30 light:bg-gray-50 rounded-lg border border-slate-600 light:border-gray-200 overflow-hidden">
        <div className="overflow-x-auto max-h-[420px]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-800 light:bg-gray-100 text-left text-xs text-slate-300 light:text-gray-600">
              <tr>
                <th className="px-3 py-2">Tag</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2">Seed</th>
                <th className="px-3 py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">Loading…</td>
                </tr>
              ) : tags.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">No tags found</td>
                </tr>
              ) : (
                tags.map((tag) => (
                  <tr
                    key={tag.id}
                    className="border-t border-slate-600/40 light:border-gray-200 hover:bg-slate-600/20 light:hover:bg-white/60"
                  >
                    <td className="px-3 py-2 text-white light:text-gray-900 font-mono text-xs">
                      {tag.display_name || tag.tag}
                      {tag.display_name && (
                        <span className="block text-slate-500 font-normal">{tag.tag}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-slate-300 light:text-gray-700">{tag.category}</td>
                    <td className="px-3 py-2 text-slate-300 light:text-gray-700">{tag.reading_type}</td>
                    <td className="px-3 py-2">
                      <span className={tag.is_active ? 'text-green-400' : 'text-slate-500'}>
                        {tag.is_active ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-slate-300 light:text-gray-700">{tag.emulator_seed}</td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1 justify-end">
                        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => startEdit(tag)}>
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-red-400"
                          onClick={() => remove(tag.id, tag.tag)}
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
