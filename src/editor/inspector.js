import { ENTITY_TYPES } from '../game/entities.js';

const PAGE_SEPARATOR = '\n---\n';

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids) if (kid) node.append(kid);
  return node;
};

function datalist(id, options) {
  const list = el('datalist', { id });
  for (const o of options) list.append(el('option', { value: o }));
  return list;
}

/**
 * Builds a property form from an entity type's schema.
 *
 * Nothing here knows what a door or a terminal is: the field list, its types,
 * and its help text all come from ENTITY_TYPES. Adding an entity type to that
 * table is enough to make it fully editable here.
 */
export function buildFields(fields, values, onChange, context = {}) {
  const form = el('div', { class: 'fields' });

  for (const [key, field] of Object.entries(fields)) {
    const row = el('label', { class: 'field' });
    row.append(el('span', { class: 'field-name', text: key }));

    const value = values[key];
    let input;

    switch (field.type) {
      case 'bool':
        input = el('input', { type: 'checkbox' });
        input.checked = !!value;
        input.addEventListener('change', () => onChange(key, input.checked));
        break;

      case 'number':
        input = el('input', { type: 'number' });
        if (field.min !== undefined) input.min = field.min;
        if (field.max !== undefined) input.max = field.max;
        input.step = field.step === undefined ? 1 : field.step;
        input.value = value === undefined ? 0 : value;
        input.addEventListener('input', () => onChange(key, Number(input.value)));
        break;

      case 'color': {
        input = el('div', { class: 'color-row' });
        const swatch = el('input', { type: 'color' });
        swatch.value = value || '#ffffff';
        const hex = el('input', { type: 'text', class: 'hex' });
        hex.value = value || '#ffffff';
        swatch.addEventListener('input', () => { hex.value = swatch.value; onChange(key, swatch.value); });
        hex.addEventListener('change', () => {
          if (/^#[0-9a-f]{6}$/i.test(hex.value)) { swatch.value = hex.value; onChange(key, hex.value); }
        });
        input.append(swatch, hex);
        break;
      }

      case 'select': {
        input = el('select');
        for (const opt of field.options) {
          input.append(el('option', { value: opt, text: opt === '' ? '(none)' : opt }));
        }
        input.value = value === undefined ? '' : value;
        input.addEventListener('change', () => onChange(key, input.value));
        break;
      }

      case 'scene': {
        input = el('select');
        const scenes = context.scenes || [];
        input.append(el('option', { value: '', text: '(none)' }));
        for (const id of scenes) input.append(el('option', { value: id, text: id }));
        if (value && !scenes.includes(value)) input.append(el('option', { value, text: `${value} (not in manifest)` }));
        input.value = value || '';
        input.addEventListener('change', () => onChange(key, input.value));
        break;
      }

      case 'flag': {
        const listId = `flags-${key}-${Math.random().toString(36).slice(2, 7)}`;
        input = el('input', { type: 'text', list: listId, placeholder: 'flag name' });
        input.value = value || '';
        input.addEventListener('input', () => onChange(key, input.value.trim()));
        row.append(datalist(listId, context.flags || []));
        break;
      }

      case 'image': {
        const listId = `imgs-${key}-${Math.random().toString(36).slice(2, 7)}`;
        input = el('input', { type: 'text', list: listId, placeholder: 'props/…' });
        input.value = value || '';
        input.addEventListener('change', () => onChange(key, input.value.trim()));
        row.append(datalist(listId, context.images || []));
        break;
      }

      case 'pages': {
        input = el('textarea', { rows: 6, placeholder: 'One page per block, separated by ---' });
        input.value = (Array.isArray(value) ? value : [value || '']).join(PAGE_SEPARATOR);
        input.addEventListener('change', () => {
          const pages = input.value.split(/\n-{3,}\n/).map((p) => p.trim()).filter((p) => p.length);
          onChange(key, pages.length ? pages : ['']);
        });
        break;
      }

      case 'text':
        input = el('textarea', { rows: 2 });
        input.value = value || '';
        input.addEventListener('change', () => onChange(key, input.value));
        break;

      default:
        input = el('input', { type: 'text' });
        input.value = value === undefined ? '' : value;
        input.addEventListener('input', () => onChange(key, input.value));
    }

    input.classList.add('control');
    row.append(input);
    if (field.help) row.append(el('span', { class: 'help', text: field.help }));
    form.append(row);
  }

  return form;
}

/** The panel for whatever is selected: an entity, a collision box, or nothing. */
export function buildInspector(container, selection, doc, context, actions) {
  container.replaceChildren();

  if (!selection) {
    container.append(el('p', { class: 'muted', text: 'Nothing selected. Click something on the canvas, or pick a tool and drag.' }));
    return;
  }

  if (selection.kind === 'rect') {
    const rect = doc.scene.collision[selection.index];
    if (!rect) return;
    container.append(el('h3', { text: 'Collision box' }));
    const fields = {
      x: { type: 'number' }, y: { type: 'number' },
      w: { type: 'number' }, h: { type: 'number' },
      type: { type: 'select', options: ['solid', 'oneway', 'ladder', 'block'],
        help: 'solid blocks all sides · oneway catches falls only · ladder is climbable' },
    };
    container.append(buildFields(fields, rect, (k, v) => {
      doc.begin();
      doc.scene.collision[selection.index][k] = v;
      doc.commit();
      actions.refresh();
    }, context));
    container.append(el('button', { class: 'danger', text: 'Delete box', onclick: () => actions.deleteSelection() }));
    return;
  }

  const entity = doc.scene.entities[selection.index];
  if (!entity) return;
  const def = ENTITY_TYPES[entity.type];

  container.append(el('h3', { text: def ? def.label : entity.type }));

  const identity = {
    id: { type: 'string', help: 'Unique within the scene.' },
    x: { type: 'number' },
    y: { type: 'number' },
    ...(def && def.resizable ? { w: { type: 'number' }, h: { type: 'number' } } : {}),
  };
  container.append(buildFields(identity, entity, (k, v) => {
    doc.begin();
    doc.scene.entities[selection.index][k] = v;
    doc.commit();
    actions.refresh();
  }, context));

  if (def) {
    container.append(el('div', { class: 'divider' }));
    container.append(buildFields(def.fields, entity.props, (k, v) => {
      doc.begin();
      doc.scene.entities[selection.index].props[k] = v;
      doc.commit();
      actions.refresh();
    }, context));
  }

  container.append(el('button', { class: 'danger', text: 'Delete entity', onclick: () => actions.deleteSelection() }));
}

export { el };
