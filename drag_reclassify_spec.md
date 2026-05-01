# Spec: Drag-to-Sidebar Reclassification

## Goal
Allow curators to reclassify cells by dragging a card (or a selection of cards) from the
main grid and dropping it onto a cell-type entry in the left sidebar. On drop, records
mutate in-memory (so the grid updates immediately) AND the action is queued to
`G.actionQueue` for eventual agent handoff.

---

## Behaviour Summary

| Scenario | What gets dragged |
|---|---|
| Drag a card that is NOT in `G.selected` | That card only (single-cell reclassify) |
| Drag any card that IS in `G.selected` | All currently selected cards as a batch |

Drop target: **sidebar cell-type items only** (elements inside `#sidebar-cells`).
Tags section items and special views (Flagged, Excluded, etc.) are **not** drop targets.

---

## 1. CSS Changes

### Drag-active state on sidebar items
Add these rules (append to the existing `<style>` block):

```css
/* ── DRAG-TO-SIDEBAR ── */
.sidebar-item.drop-target {
  /* shown whenever a drag is in progress over a cell-type sidebar item */
  padding-top: 12px;
  padding-bottom: 12px;
  border-left-width: 4px;
  transition: padding .15s, border-left-width .15s, background .15s;
}
body.dragging-cell .sidebar-item[data-cell-type] {
  /* expand ALL cell-type sidebar items during any drag */
  padding-top: 11px;
  padding-bottom: 11px;
  cursor: cell;
}
body.dragging-cell .sidebar-item[data-cell-type] .si-label::after {
  content: ' ↙';
  font-size: 10px;
  color: var(--text4);
  margin-left: 4px;
}
.sidebar-item.drag-over {
  background: var(--accent-light);
  border-left-color: var(--accent);
  border-left-width: 4px;
}
.cell-card.is-dragging {
  opacity: .45;
  outline: 2px dashed var(--accent);
  outline-offset: 2px;
}
```

### Sidebar item data attribute
The correct target function is **`renderSidebarCells()`**. The iterator variable inside
that loop is `lbl`. Add one line directly below the existing `d.dataset.view = lbl`:

```js
d.dataset.view    = lbl;
d.dataset.cellType = lbl;   // NEW — used by drop handler
```

Also call `attachSidebarDropTargets()` at the very end of `renderSidebarCells()`, so
the listeners re-bind every time sidebar counts re-render (which happens after each drop).

---

## 2. Cell Card — Make Draggable

In the card-rendering function (look for where `.cell-card` elements are created and
`innerHTML` / `onclick` is assigned), add:

```js
card.draggable = true;

card.addEventListener('dragstart', e => {
  // Guard: if the drag originated from the selection checkbox, suppress it.
  // In selection mode the checkbox is the primary interaction target — a drag
  // starting there is almost certainly an accidental click-drag, not intent.
  if (e.target.closest('.card-checkbox')) { e.preventDefault(); return; }

  // Determine drag set
  const isPartOfSelection = G.selected && G.selected.has(filename);
  G._dragFilenames = isPartOfSelection
    ? Array.from(G.selected)
    : [filename];

  // Visual feedback on dragging card(s)
  card.classList.add('is-dragging');
  document.body.classList.add('dragging-cell');

  // Custom drag ghost for multi-card drags so the count is visible
  if (isPartOfSelection && G.selected.size > 1) {
    const badge = document.createElement('div');
    badge.style.cssText = 'position:absolute;top:-1000px;background:var(--accent);color:#fff;padding:4px 10px;border-radius:6px;font-weight:700;font-family:DM Sans,sans-serif;font-size:13px;';
    badge.textContent = `Moving ${G.selected.size} cells`;
    document.body.appendChild(badge);
    e.dataTransfer.setDragImage(badge, 0, 0);
    setTimeout(() => badge.remove(), 0);
  }

  // Pack a lightweight payload (used as fallback; real data is in G._dragFilenames)
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', filename);
});

card.addEventListener('dragend', () => {
  card.classList.remove('is-dragging');
  document.body.classList.remove('dragging-cell');
  // Clean up any lingering drag-over highlights
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  G._dragFilenames = null;
});
```

---

## 3. Sidebar Drop Targets

After the sidebar is rendered (end of whatever function builds `#sidebar-cells`),
call a new helper `attachSidebarDropTargets()`:

```js
function attachSidebarDropTargets() {
  document.querySelectorAll('.sidebar-item[data-cell-type]').forEach(item => {
    const targetLabel = item.dataset.cellType;

    item.addEventListener('dragover', e => {
      if (!G._dragFilenames) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      item.classList.add('drag-over');
    });

    item.addEventListener('dragleave', e => {
      // Only remove if leaving the item itself, not a child
      if (!item.contains(e.relatedTarget)) {
        item.classList.remove('drag-over');
      }
    });

    item.addEventListener('drop', e => {
      e.preventDefault();
      item.classList.remove('drag-over');
      document.body.classList.remove('dragging-cell');

      const filenames = G._dragFilenames;
      if (!filenames || !filenames.length) return;

      const user = G.userName || 'curator';
      const ts = now();
      let n = 0;

      filenames.forEach(fn => {
        const rec = G.records[fn];
        if (!rec) return;
        const prevLabel = rec.path_label || rec.tech_label || '—';
        if (prevLabel === targetLabel) return;  // no-op if already correct type

        // ── In-memory mutation ──
        rec.path_label    = targetLabel;
        rec.path_status   = 'finalized';
        rec.path_id       = user;
        rec.path_date     = ts;
        rec.path_review_method = 'drag';
        rec.version       += 1;
        rec.last_modified_by   = user;
        rec.last_modified_date = ts;
        // Clear any existing correction_label — drag IS the new authoritative label.
        // Without this, effectiveLabel() would still return the old correction_label
        // and the card would visually appear unchanged even though path_label updated.
        rec.correction_label  = '';
        rec.correction_reason = '';
        rec.correction_by     = '';
        rec.correction_date   = '';
        rec.audit_trail.push({
          user, role: 'path',
          action: `Drag reclassify: ${prevLabel} → ${targetLabel}`,
          timestamp: ts, version: rec.version
        });

        // ── Agent payload queue — use existing helper ──
        // queueAction handles timestamp, session_id, and badge update automatically
        queueAction({
          image_id:  rec.image_id,
          filename:  fn,
          action:    'reclassify',
          prevLabel,
          newLabel:  targetLabel,
          method:    'drag'
        });

        n++;
      });

      G._dragFilenames = null;

      if (n === 0) {
        toast('⚠ Nothing to reclassify — cells already that type.');
        return;
      }

      // ── Local DOM update — do NOT call refreshAll() ──
      // refreshAll() nukes the grid innerHTML and resets the IntersectionObserver
      // cursor, snapping the curator back to the top of a long scroll. Instead,
      // mutate each card in place or remove it if it no longer belongs in the view.
      filenames.forEach(fn => {
        const rec = G.records[fn];
        if (!rec) return;
        const card = document.getElementById('card-' + rec.image_id);
        if (!card) return;

        // Determine whether this card still belongs in the current view.
        // A card must pass three checks: view type, active filter, and search query.
        const inTypedView = G.currentView !== 'all'
          && G.currentView !== 'pending'
          && G.currentView !== 'flagged';
        const failsFilter = G.currentFilter && G.currentFilter !== 'all'
          && rec.path_status !== G.currentFilter;
        const failsSearch = G.searchQuery
          && !fn.toLowerCase().includes(G.searchQuery)
          && !(rec.path_label||'').toLowerCase().includes(G.searchQuery);

        if (inTypedView || failsFilter || failsSearch) {
          card.remove();
        } else {
          // Update the label in place. Aberration cells display their tag name as the
          // title (not path_label), so respect that logic rather than overwriting blindly.
          const isAberration = (rec.tags||'').split(',').map(t=>t.trim()).includes('aberration');
          const labelEl = card.querySelector('.cell-card-label');
          if (labelEl && !isAberration) {
            labelEl.textContent = CELL_DISPLAY[targetLabel] || targetLabel;
          }
          const metaEl = card.querySelector('.cell-card-meta');
          if (metaEl) metaEl.innerHTML = '<span class="cc-pill fin">finalized</span>';
          // Strip the correction styling now that correction_label is cleared
          card.classList.remove('corrected');
          card.querySelector('.card-flag-dot.correction')?.remove();
        }
      });

      // Update sidebar counts and header stats to reflect the moves.
      // renderSidebarCells() handles per-type counts; updateHeaderStats() (or its
      // equivalent — check the actual function name in admin.html) updates the
      // "All / Pending / Approved" aggregate badges in the header and sidebar top.
      renderSidebarCells();   // re-renders counts; also re-attaches drop targets
      if (typeof updateHeaderStats === 'function') updateHeaderStats();

      const displayName = CELL_DISPLAY[targetLabel] || targetLabel;
      toast(`✅ ${n} cell${n === 1 ? '' : 's'} reclassified as ${displayName}`);
      clearSelection();
    });
  });
}
```

---

## 4. Agent Payload Integration

The drop handler calls `queueAction({ ..., action: 'reclassify', ... })`, which is the
existing helper already used by other action types. It stamps `timestamp` and `session_id`
and calls `updatePayloadBadge()` automatically — no additional wiring needed.

If `generatePayload()` / `showPayloadModal()` only handles specific action types (e.g.
only `approve` and `exclude`), extend its switch/if block to also render `reclassify` rows:

```
Reclassify {filename} ({image_id}): {prevLabel} → {newLabel}  [drag]
```

---

## 5. Edge Cases

| Case | Handling |
|---|---|
| Drop onto current view's cell type (no label change) | `if (prevLabel === targetLabel) return` — skipped silently per cell, toast only if all were no-ops |
| Drag while `G.userName` is unset | Use `'curator'` as fallback — don't block the action with a prompt |
| Drop onto non-cell-type sidebar item (tags, aberrations, etc.) | No `data-cell-type` attribute → no drop handlers attached → browsers show default "not allowed" cursor |
| Drag multiple selected, some already the target type | Skip those silently, count only changed ones in the toast |
| Cell has an active `correction_label` | Clear `correction_label` and related fields on drop — drag is the new authoritative label; card `corrected` class and flag dot removed in-place |
| Aberration-tagged cell dragged in a general view | Label element **not** overwritten — aberration cells use tag-derived titles; only the status pill and `corrected` styling are updated |
| Active search or filter when dragging | Card removed from view if it no longer matches the search/filter after reclassify, rather than left visible with a stale filter match |
| Checkbox clicked during selection mode | `dragstart` suppressed if `e.target.closest('.card-checkbox')` — prevents accidental drags on checkbox interaction |

---

## 6. Validation

After implementation, run the acorn parser check:

```
node -e "require('acorn').parse(require('fs').readFileSync('admin.html','utf8').match(/<script[^>]*>([\s\S]*?)<\/script>/i)[1], {ecmaVersion:2020, sourceType:'script'})"
```

Smoke-test:
1. Single-card drag onto a different sidebar type → card disappears from current view (if typed view) or label updates in place (if "all" view), toast appears, payload badge increments
2. Select 3 cards → drag one → drag ghost shows "Moving 3 cells" badge → all 3 reclassify
3. Drag onto same cell type → toast warns, no mutation, no payload entry
4. Open payload modal → drag actions appear grouped with other reclassify actions
5. Scroll down to card 400, drag it → confirm scroll position does not reset
6. Drag a cell that has a `correction_label` set → card loses its purple `corrected` border, correction pill disappears, label shows the new type
7. Type a search query, scroll, then drag a visible card → card removed if it no longer matches the search after relabel
8. Drag an aberration-tagged cell in "All" view → status pill updates but the tag-derived label text is not overwritten
