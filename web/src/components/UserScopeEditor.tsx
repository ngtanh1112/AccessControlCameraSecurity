import { useEffect, useState } from "react";

import type { ManagedUser } from "../api/client";

type ZoneOption = { id: string; name: string };

type Props = {
  title: string;
  user: ManagedUser;
  zones: readonly ZoneOption[];
  onSave: (zoneIds: string[]) => Promise<void>;
  disabled?: boolean;
};

export function UserScopeEditor({ title, user, zones, onSave, disabled = false }: Props) {
  const [selected, setSelected] = useState<string[]>(user.zone_ids);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => setSelected(user.zone_ids), [user.id, user.zone_ids]);

  function toggle(zoneId: string) {
    setSelected((current) => current.includes(zoneId) ? current.filter((id) => id !== zoneId) : [...current, zoneId]);
  }

  async function save() {
    setIsSaving(true);
    try {
      await onSave(selected);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="scope-editor" aria-label={`${title} for ${user.username}`}>
      <div className="scope-editor-heading"><div><p className="field-label">{title}</p><h3>{user.display_name}</h3><span>@{user.username}</span></div></div>
      <div className="zone-options">
        {zones.map((zone) => <label key={zone.id} className="zone-option"><input type="checkbox" checked={selected.includes(zone.id)} onChange={() => toggle(zone.id)} disabled={disabled || isSaving} /><span>{zone.name}</span></label>)}
      </div>
      {!disabled && <button className="secondary-button" type="button" onClick={() => void save()} disabled={isSaving}>{isSaving ? "Saving…" : "Save scope"}</button>}
    </section>
  );
}
