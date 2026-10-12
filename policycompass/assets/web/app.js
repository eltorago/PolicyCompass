'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const main = $('#main');
const fragment = new URLSearchParams(location.hash.slice(1));
let session = fragment.get('session');
try {
  if (session) sessionStorage.setItem('policycompass-session', session);
  else session = sessionStorage.getItem('policycompass-session');
} catch (_) { /* The current launch still works when browser storage is disabled. */ }
history.replaceState(null, '', location.pathname);

const state = {page: 'new', status: null, comparison: null, files: [], appendId: null,
  tab: 'Overview', handledJob: null, busy: false, uploading: false, quit: false};
const statuses = ['Mentioned', 'Related wording', 'Not mentioned', 'Unable to check'];
const statusClass = value => ({'Mentioned':'mentioned', 'Related wording':'related', 'Not mentioned':'missing', 'Unable to check':'unable'}[value] || '');
const titles = {new:'New comparison', library:'Saved comparisons', results:'Results', frameworks:'Framework updates', settings:'Settings & help'};

function notice(message, error = false) {
  const box = $('#notice');
  box.textContent = message;
  box.className = error ? 'error' : 'note';
  box.hidden = !message;
}
function guarded(action) {
  return (...args) => Promise.resolve().then(() => action(...args)).catch(error => notice(error.message, true));
}
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), guarded(value));
    else if (key === 'class') node.className = value;
    else if (key === 'checked' || key === 'disabled' || key === 'hidden' || key === 'multiple' || key === 'required') node[key] = value;
    else if (key === 'value') node.value = value;
    else if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  for (const child of children.flat(Infinity)) {
    if (child !== null && child !== undefined) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
function button(label, action, className = '', mutates = false) {
  return el('button', {type:'button', class:className, onClick:action, 'data-mutates':mutates ? 'true' : null, disabled:mutates && state.busy}, label);
}
function field(label, input, hint = '') {
  return el('label', {class:'field'}, label, input, hint ? el('small', {}, hint) : null);
}
function select(options, value, attrs = {}) {
  const node = el('select', attrs, options.map(([key, label]) => el('option', {value:key}, label)));
  node.value = value;
  return node;
}
function checkbox(label, checked, hint = '', attrs = {}) {
  return el('label', {class:'check'}, el('input', {type:'checkbox', checked, ...attrs}), el('span', {}, label, hint ? el('small', {}, hint) : null));
}
function heading(title, subtitle) {
  return [el('p', {class:'eyebrow'}, 'POLICYCOMPASS'), el('h1', {}, title), el('p', {class:'intro'}, subtitle)];
}
function date(value) { return new Date(value).toLocaleString('en-AU'); }
function badge(value) { return el('span', {class:'badge ' + statusClass(value)}, value); }
function locationText(locator) {
  return Object.entries(locator || {}).filter(([key, value]) => value !== null && !['start','end','boundingBox'].includes(key))
    .map(([key,value]) => `${key}: ${value}`).join(' · ');
}
function link(label, url) {
  try {
    const parsed = new URL(url);
    if (!['https:', 'http:'].includes(parsed.protocol)) return el('span', {}, label);
    return el('a', {href:parsed.href, target:'_blank', rel:'noopener noreferrer'}, label);
  } catch (_) { return el('span', {}, label); }
}
async function api(path, data, options = {}) {
  const headers = {'X-PolicyCompass-Token':session || '', ...(options.headers || {})};
  const request = {headers, credentials:'omit', cache:'no-store', ...options};
  request.headers = headers;
  if (data !== undefined) {
    request.method = 'POST';
    headers['Content-Type'] = 'application/json';
    request.body = JSON.stringify(data);
  }
  let response;
  try { response = await fetch(path, request); }
  catch (_) { throw new Error('The local application is not responding. Reopen PolicyCompass using its shortcut.'); }
  if (!response.ok) {
    let message = 'The operation could not finish.';
    try { message = (await response.json()).error || message; } catch (_) { /* Keep the readable fallback. */ }
    throw new Error(message);
  }
  return response;
}
async function json(path, data) { return (await api(path, data)).json(); }
async function upload(file, kind) {
  const limit = kind === 'assessment' ? 128 : 16;
  if (!file.size || file.size > limit * 1024 * 1024) throw new Error(`Choose a non-empty file no larger than ${limit} MiB.`);
  const allowed = {policy:/\.(pdf|docx|txt|md|zip)$/i, framework:/\.(pdf|xlsx|json|html)$/i, assessment:/\.policycompass$/i};
  if (!allowed[kind]?.test(file.name)) throw new Error('This file type is not supported for that import.');
  return (await api('/api/upload?' + new URLSearchParams({name:file.name, kind}), undefined,
    {method:'POST', headers:{'Content-Type':'application/octet-stream'}, body:file})).json();
}
async function download(path, filename) {
  const response = await api(path);
  const url = URL.createObjectURL(await response.blob());
  const anchor = el('a', {href:url, download:filename});
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
function params(extra = {}) {
  return new URLSearchParams({id:state.comparison.id, run:state.comparison.report.runId, ...extra});
}
function syncBusy() {
  document.querySelectorAll('[data-mutates="true"]').forEach(node => { node.disabled = state.busy; });
}
async function jobStarted(job) {
  state.busy = true;
  state.handledJob = null;
  state.status.job = job;
  showJob();
}
function showJob() {
  const job = state.status.job;
  state.busy = job.status === 'running' || state.uploading;
  $('#job').hidden = job.status !== 'running';
  $('#job-message').textContent = job.message;
  $('#cancel').disabled = !state.busy;
  syncBusy();
}
async function refreshStatus() {
  if (state.quit) return;
  state.status = await json('/api/status');
  $('#version').textContent = 'Version ' + state.status.version;
  showJob();
  const job = state.status.job;
  if (job.id && job.status !== 'running' && job.id !== state.handledJob) {
    state.handledJob = job.id;
    if (job.status === 'succeeded') {
      if (job.result?.comparisonId) {
        await openComparison(job.result.comparisonId);
        notice('Comparison saved in this workspace. Download a copy to keep it elsewhere.');
      } else if (job.kind === 'update') {
        await showPage('frameworks');
        showUpdates(job.result.updates);
      }
    } else if (job.status === 'failed') notice(job.message, true);
    else if (job.status === 'cancelled') {
      notice(job.kind === 'update' ? 'Update cancelled. Any frameworks completed before cancellation remain available.' : job.message);
      if (state.page === 'frameworks') await showPage('frameworks');
    }
  }
}
async function poll() {
  try { await refreshStatus(); }
  catch (error) { if (!state.quit) notice(error.message, true); }
  if (!state.quit) setTimeout(poll, 2000);
}

async function showPage(page) {
  if (page === 'results' && !state.comparison) return;
  state.page = page;
  document.querySelectorAll('[data-page]').forEach(node => {
    if (node.dataset.page === page) node.setAttribute('aria-current', 'page');
    else node.removeAttribute('aria-current');
  });
  $('#breadcrumb').textContent = 'Workspace / ' + titles[page];
  main.replaceChildren();
  if (page === 'new') renderNew();
  else if (page === 'library') await renderLibrary();
  else if (page === 'frameworks') renderFrameworks();
  else if (page === 'settings') renderSettings();
  else renderResults();
  syncBusy();
}
function frameworkChecks(selected, installedOnly = false) {
  const installed = new Map(state.status.installed.availableFrameworks.map(row => [row.id, row]));
  return el('div', {class:'checks'}, state.status.frameworks.map(fw => {
    const available = installed.get(fw.id);
    return checkbox(fw.title, selected.includes(fw.id) && (!installedOnly || !!available),
      available ? `${available.requirements.toLocaleString()} requirements · ${available.edition}` : 'Download or import this framework first',
      {name:'framework', value:fw.id, disabled:installedOnly && !available});
  }));
}
function selectedFrameworks(container) {
  return [...container.querySelectorAll('input[name="framework"]:checked')].map(node => node.value);
}
function maturityField(value) {
  return field('ISM / Essential Eight filter', select([['','All ISM controls'], ['ML1','Maturity level 1'], ['ML2','Maturity level 2'], ['ML3','Maturity level 3']], value || '', {name:'ismMaturity'}), 'Applies only when ISM is selected. This does not assign a maturity rating.');
}
function renderNew() {
  const previous = state.appendId ? state.comparison.report : null;
  const settings = state.status.settings;
  main.append(...heading(previous ? 'Compare a new revision' : 'Start a policy comparison',
    'Choose your documents and frameworks. PolicyCompass finds related passages and shows which requirements need a closer look.'));
  const installed = state.status.installed.availableFrameworks;
  if (!installed.length) main.append(el('div', {class:'card note'}, el('h2', {}, 'First, add a framework'),
    el('p', {}, 'Download the frameworks you use. They stay on this computer for future comparisons, including offline use.'),
    button('Set up frameworks', () => showPage('frameworks'))));
  const form = el('form', {class:'grid', onSubmit:async event => {
    event.preventDefault();
    if (state.busy) throw new Error('Wait for the current operation to finish.');
    const values = new FormData(form);
    const frameworks = selectedFrameworks(form);
    const job = await json('/api/compare', {uploads:state.files.map(file => file.id), frameworks,
      name:values.get('name'), scope:values.get('scope'), organisation:values.get('organisation'),
      documentStatus:values.get('documentStatus'), retention:values.get('retention'),
      ismMaturity:frameworks.includes('ism') ? values.get('ismMaturity') : '', comparisonId:state.appendId});
    state.files = []; renderFiles(); notice(''); await jobStarted(job);
  }});
  const name = el('input', {name:'name', value:previous?.name || 'Policy review', maxlength:'500', required:true});
  const scope = el('textarea', {name:'scope', maxlength:'4000', required:true, placeholder:'For example, the approved policies covering staff access and incident response.'});
  scope.value = previous?.scope.description || '';
  const files = el('ul', {class:'file-list', 'aria-label':'Selected documents'});
  const renderFiles = () => files.replaceChildren(...state.files.map(file => el('li', {}, el('span', {}, file.name),
    el('small', {}, `${Math.ceil(file.size / 1024).toLocaleString()} KB`), button('Remove', async () => {
      await json('/api/discard', {uploads:[file.id]}); state.files = state.files.filter(item => item.id !== file.id); renderFiles();
    }, 'quiet', true))));
  async function addFiles(selected) {
    if (state.busy) throw new Error('Wait for the current operation to finish.');
    const list = [...selected];
    if (!list.length) return;
    if (list.length + state.files.length > 250) throw new Error('Select up to 250 files at a time.');
    state.uploading = true; state.busy = true; syncBusy();
    try {
      for (let index = 0; index < list.length; index++) {
        notice(`Adding file ${index + 1} of ${list.length}: ${list[index].name}`);
        state.files.push(await upload(list[index], 'policy'));
        renderFiles();
      }
      notice('');
    } finally { state.uploading = false; state.busy = state.status.job.status === 'running'; syncBusy(); }
  }
  const picker = el('input', {type:'file', multiple:true, accept:'.pdf,.docx,.txt,.md,.zip', 'aria-label':'Choose policy documents', 'data-mutates':'true',
    onChange:async event => { const selected = [...event.target.files]; event.target.value = ''; await addFiles(selected); }});
  const drop = el('div', {class:'dropzone', onDragover:event => {event.preventDefault(); drop.classList.add('drag');},
    onDragleave:() => drop.classList.remove('drag'), onDrop:async event => {event.preventDefault();drop.classList.remove('drag');await addFiles(event.dataTransfer.files);}},
    el('strong', {}, 'Drop your policy files here'), el('p', {class:'muted'}, 'Word, text PDF, Markdown, text or ZIP · up to 16 MiB per file'), picker);
  const left = el('section', {class:'card'}, el('h2', {}, '1. Describe the comparison'),
    el('div', {class:'stack'}, field('Comparison name', name), field('Documents in scope', scope),
      field('Organisation (optional)', el('input', {name:'organisation', value:previous?.organisation || settings.organisation, maxlength:'500'}))),
    el('h2', {class:'actions'}, '2. Add policy documents'), drop, files);
  renderFiles();
  const choices = previous ? previous.versions.frameworks.map(fw => fw.id) : settings.frameworks;
  const right = el('section', {class:'card'}, el('h2', {}, '3. Choose frameworks'), frameworkChecks(choices, true),
    button('Manage frameworks', () => showPage('frameworks'), 'quiet'), el('div', {class:'stack actions'}, maturityField(settings.ismMaturity),
      field('Document status', select([['unknown','Not specified'], ['approved','Approved'], ['draft','Draft'], ['superseded','Superseded']], 'unknown', {name:'documentStatus'})),
      field('Keep text in the saved comparison', select([['extracted','All extracted text'], ['evidence','Matching passages only']], settings.retention, {name:'retention'}))),
    previous ? el('p', {class:'note actions'}, 'This adds a run to the same comparison. Earlier runs and their framework editions remain available in History.') : null,
    el('div', {class:'actions'}, el('button', {type:'submit', 'data-mutates':'true'}, 'Compare and save')),
    el('p', {class:'muted actions'}, 'Results are saved automatically on this computer. Originals are used only during import; saved comparisons keep the text you select above.'));
  form.append(left, right); main.append(form);
}

async function renderLibrary() {
  main.append(...heading('Saved comparisons', 'Reopen a comparison, review an earlier run or import a saved .policycompass file.'));
  const picker = el('input', {type:'file', accept:'.policycompass', 'aria-label':'Import a saved comparison', 'data-mutates':'true', onChange:async event => {
    const file = event.target.files[0]; if (!file) return;
    event.target.value = ''; notice('Adding the saved comparison…');
    const item = await upload(file, 'assessment');
    await jobStarted(await json('/api/import', {upload:item.id})); notice('');
  }});
  main.append(el('div', {class:'card row spread'}, el('div', {}, el('h2', {}, 'Import a comparison'),
    el('p', {class:'muted'}, 'The original file stays unchanged. Its history is copied into this workspace.')), picker));
  const rows = await json('/api/library');
  if (state.page !== 'library') return;
  if (!rows.length) {main.append(el('div', {class:'card empty'}, el('h2', {}, 'No comparisons saved yet'),
    el('p', {}, 'Create your first comparison or import an existing file.'), button('New comparison', () => {state.appendId = null;return showPage('new');}))); return;}
  main.append(el('div', {class:'card table-wrap'}, el('table', {},
    el('thead', {}, el('tr', {}, ['Comparison', 'Frameworks', 'Runs', 'Last saved', ''].map(title => el('th', {}, title)))),
    el('tbody', {}, rows.map(row => el('tr', {}, el('td', {}, el('strong', {}, row.name), el('br'), el('small', {}, row.organisation)),
      el('td', {}, row.frameworks.join(', ')), el('td', {}, row.runs), el('td', {}, date(row.updatedAt)),
      el('td', {}, button('Open', () => openComparison(row.id), 'secondary'))))))));
}

function renderFrameworks() {
  main.append(...heading('Framework updates', 'Download official publisher files once, then use them locally. Existing comparisons keep the editions they used.'));
  const installed = new Map(state.status.installed.availableFrameworks.map(fw => [fw.id, fw]));
  const automatic = el('div', {class:'checks'}, state.status.frameworks.filter(fw => fw.automatic).map(fw => {
    const ready = installed.get(fw.id);
    return checkbox(fw.title, state.status.settings.frameworks.includes(fw.id),
      ready ? `${ready.edition} · ${ready.requirements.toLocaleString()} requirements` : 'Not downloaded', {name:'framework', value:fw.id});
  }));
  const results = el('div', {id:'update-results'});
  const downloadCard = el('section', {class:'card'}, el('h2', {}, 'Download from publishers'),
    el('p', {class:'muted'}, 'Choose the frameworks you need. This step requires internet access.'), automatic,
    el('div', {class:'actions'}, button('Download selected frameworks', async () => {
      await jobStarted(await json('/api/update', {frameworks:selectedFrameworks(automatic)})); notice('');
    }, '', true)), results);
  const manualKey = select(state.status.frameworks.map(fw => [fw.id, fw.title]), 'aescsf', {'aria-label':'Framework to import'});
  const manualFile = el('input', {type:'file', accept:'.pdf,.xlsx,.json,.html', 'aria-label':'Downloaded framework file', 'data-mutates':'true'});
  const importCard = el('section', {class:'card'}, el('h2', {}, 'Import a publisher file'),
    el('p', {}, 'For AESCSF, download the Core workbook from AEMO, then select it below. No renaming or moving files is needed.'),
    el('p', {}, link('Open the AEMO download page', state.status.frameworks.find(fw => fw.id === 'aescsf').source)),
    el('div', {class:'stack'}, field('Framework', manualKey), field('Publisher file', manualFile)),
    el('div', {class:'actions'}, button('Import framework file', async () => {
      if (!manualFile.files[0]) throw new Error('Choose a downloaded publisher file first.');
      notice('Adding the framework file…'); const item = await upload(manualFile.files[0], 'framework'); manualFile.value = '';
      await jobStarted(await json('/api/update', {frameworks:[manualKey.value], upload:item.id})); notice('');
    }, '', true)), el('p', {class:'muted actions'}, 'You can also import a publisher file here when an automatic download fails.'));
  main.append(el('div', {class:'grid'}, downloadCard, importCard));
  main.append(el('section', {class:'card'}, el('h2', {}, 'Available on this computer'),
    installed.size ? el('div', {class:'table-wrap'}, el('table', {},
      el('thead', {}, el('tr', {}, ['Framework', 'Edition', 'Requirements', 'Publisher'].map(title => el('th', {}, title)))),
      el('tbody', {}, [...installed.values()].map(fw => el('tr', {}, el('td', {}, fw.title), el('td', {}, fw.edition),
        el('td', {}, fw.requirements.toLocaleString()), el('td', {}, link('Source', state.status.frameworks.find(row => row.id === fw.id)?.source))))))) :
      el('p', {class:'muted'}, 'No frameworks have been downloaded or imported yet.')));
  if (state.status.frameworkError) main.append(el('p', {class:'note warning'}, state.status.frameworkError));
}
function showUpdates(results) {
  const container = $('#update-results');
  if (!container) return;
  container.replaceChildren(...results.map(row => el('div', {class:'note actions ' + (row.status === 'Failed' ? 'warning' : '')},
    el('strong', {}, `${state.status.frameworks.find(fw => fw.id === row.framework)?.title || row.framework}: ${row.status}`),
    el('p', {}, row.message || `${row.edition} · ${row.requirements.toLocaleString()} requirements`))));
  notice(results.some(row => row.status === 'Failed') ? 'Some frameworks could not be updated. See the details below; previous versions are retained.' : 'Frameworks are ready to use.');
}

async function openComparison(id, run = null) {
  const query = new URLSearchParams({id}); if (run) query.set('run', run);
  const comparison = await json('/api/comparison?' + query);
  state.comparison = comparison;
  state.tab = 'Overview';
  $('[data-page="results"]').disabled = false;
  await showPage('results');
}
function renderResults() {
  const {report, history: runs, metadata} = state.comparison;
  main.append(...heading(report.name, report.scope.description));
  const controls = el('div', {class:'row spread'}, el('div', {class:'row'},
    el('span', {class:'muted'}, `${report.organisation ? report.organisation + ' · ' : ''}${date(report.analysisDate)}`),
    metadata.historical ? badge('Earlier run') : badge('Latest run')),
    el('div', {class:'row'}, button('Compare new documents', () => {state.appendId = state.comparison.id; return showPage('new');}, 'secondary', true),
      button('Download comparison', () => download('/api/assessment?' + params(), 'PolicyCompass-comparison.policycompass'), 'secondary')));
  main.append(controls);
  for (const message of report.limitations) main.append(el('p', {class:'note warning actions'}, message));
  main.append(el('div', {class:'metrics'}, statuses.map(status => el('div', {class:'metric ' + statusClass(status)},
    el('strong', {}, report.summary.counts[status].toLocaleString()), el('span', {}, status)))));
  const content = el('div', {id:'result-content'});
  const tabs = el('div', {class:'subtabs', role:'tablist', 'aria-label':'Comparison results'});
  for (const name of ['Overview', 'Requirements', 'Not mentioned', 'Documents', 'Relationships', 'Reports', 'History']) {
    tabs.append(button(name, () => {state.tab = name; renderResultsTab(content, report, runs, tabs);}, name === state.tab ? 'active' : ''));
  }
  main.append(tabs, content); renderResultsTab(content, report, runs, tabs);
}
function renderResultsTab(content, report, runs, tabs) {
  [...tabs.children].forEach(node => {node.className = node.textContent === state.tab ? 'active' : ''; node.setAttribute('aria-pressed', String(node.textContent === state.tab));});
  content.replaceChildren();
  if (state.tab === 'Overview') {
    content.append(el('div', {class:'card table-wrap'}, el('h2', {}, 'Framework breakdown'), el('table', {},
      el('thead', {}, el('tr', {}, ['Framework', 'Edition', 'Requirements', ...statuses].map(title => el('th', {}, title)))),
      el('tbody', {}, report.frameworkSummaries.map(fw => el('tr', {}, el('td', {}, el('strong', {}, fw.title)), el('td', {}, fw.edition),
        el('td', {}, fw.requirements.toLocaleString()), statuses.map(status => el('td', {}, fw.counts[status].toLocaleString()))))))),
      el('div', {class:'grid'}, el('section', {class:'card'}, el('h2', {}, 'Read the passages before deciding'),
        el('p', {}, 'A match describes wording in the selected policies. It does not prove that a control operates or that an organisation complies with a framework.'),
        button('Review requirements', () => {state.tab='Requirements';renderResultsTab(content,report,runs,tabs);}, 'secondary')),
      el('section', {class:'card'}, el('h2', {}, 'Check the scope'),
        el('p', {}, `${report.documents.length} documents · ${report.summary.requirements.toLocaleString()} requirements`),
        el('p', {class:'muted'}, 'Each framework is checked independently. Requirements without matching wording may be covered elsewhere or expressed differently.'))));
  } else if (state.tab === 'Requirements' || state.tab === 'Not mentioned') renderRequirements(content, report);
  else if (state.tab === 'Documents') renderDocuments(content, report);
  else if (state.tab === 'Relationships') {
    content.append(el('section', {class:'card'}, el('h2', {}, 'Framework relationships'),
      el('p', {class:'muted'}, 'These links provide context. A link does not count as policy evidence or transfer a result between frameworks.'),
      report.mappings.length ? el('div', {class:'table-wrap'}, el('table', {}, el('thead', {}, el('tr', {},
        ['Source', 'Relationship', 'Target'].map(label => el('th', {}, label)))),
        el('tbody', {}, report.mappings.map(row => el('tr', {}, el('td', {}, row.source), el('td', {}, row.relationship), el('td', {}, row.target)))))) :
        el('p', {}, 'No publisher relationships are included between the frameworks in this run.')));
  } else if (state.tab === 'Reports') renderReports(content, report);
  else if (state.tab === 'History') {
    content.append(el('section', {class:'card'}, el('h2', {}, 'Saved runs'), el('p', {class:'muted'}, 'Each run keeps its document text, results and framework editions. Download comparison includes the full history.'),
      [...runs].reverse().map((run, index) => el('div', {class:'history-item'}, el('div', {}, el('strong', {}, date(run.createdAt)), el('br'),
        el('small', {}, index === 0 ? 'Latest saved run' : 'Earlier run')), run.id === report.runId ? badge('Currently open') :
        button('Open run', () => openComparison(state.comparison.id, run.id), 'secondary')))));
  }
}
function renderRequirements(container, report) {
  const gaps = state.tab === 'Not mentioned';
  const card = el('section', {class:'card'});
  const search = el('input', {type:'search', class:'search', placeholder:'Search requirement wording or reference', 'aria-label':'Search requirements'});
  const framework = select([['','All frameworks'], ...report.versions.frameworks.map(fw => [fw.id, fw.title])], '', {'aria-label':'Filter by framework'});
  const status = select([['','All statuses'], ...statuses.map(value => [value,value])], gaps ? 'Not mentioned' : '', {'aria-label':'Filter by alignment status'});
  const body = el('tbody'); const pager = el('div', {class:'pager'}); const detail = el('div', {class:'details'});
  let page = 0;
  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    const rows = report.requirements.filter(row => (!framework.value || row.frameworkId === framework.value)
      && (!status.value || row.alignment.status === status.value)
      && (!query || [row.id,row.authoritativeText,row.heading,row.context].join(' ').toLocaleLowerCase().includes(query)));
    const pages = Math.max(1, Math.ceil(rows.length / 75)); page = Math.min(page,pages - 1);
    body.replaceChildren(...rows.slice(page*75, page*75+75).map(row => el('tr', {},
      el('td', {}, button(row.id, () => renderRequirementDetail(detail, row, report), 'link')),
      el('td', {}, row.authoritativeText.slice(0,210) + (row.authoritativeText.length > 210 ? '…' : '')),
      el('td', {}, badge(row.alignment.status)), el('td', {}, row.alignment.matchCount))));
    if (!rows.length) body.append(el('tr', {}, el('td', {colspan:'4', class:'empty'}, 'No requirements match these filters.')));
    const previous = button('Previous', () => {page--;render();}, 'quiet'); previous.disabled = page === 0;
    const next = button('Next', () => {page++;render();}, 'quiet'); next.disabled = page + 1 >= pages;
    pager.replaceChildren(el('span', {}, `${rows.length.toLocaleString()} requirements · page ${page + 1} of ${pages}`), el('div', {class:'row'}, previous, next));
  }
  let searchTimer;
  search.addEventListener('input', () => {clearTimeout(searchTimer);searchTimer=setTimeout(() => {page=0;render();},150);});
  framework.addEventListener('change', () => {page=0;render();}); status.addEventListener('change', () => {page=0;render();});
  card.append(el('div', {class:'filters'}, search, framework, status), el('div', {class:'table-wrap'}, el('table', {},
    el('thead', {}, el('tr', {}, ['Reference', 'Framework requirement', 'Alignment', 'Passages'].map(label => el('th', {}, label)))), body)), pager);
  container.append(card, detail); render();
}
function highlighted(text, spans) {
  const node = el('p', {class:'passage'}); const chars = Array.from(text); let cursor = 0;
  for (const span of [...spans].sort((a,b) => a.start - b.start)) {
    const start = Math.max(cursor, Math.min(chars.length, span.start)); const end = Math.max(start, Math.min(chars.length, span.end));
    node.append(document.createTextNode(chars.slice(cursor,start).join('')), el('mark', {}, chars.slice(start,end).join(''))); cursor=end;
  }
  node.append(document.createTextNode(chars.slice(cursor).join(''))); return node;
}
function renderRequirementDetail(container, row, report) {
  container.replaceChildren(el('section', {class:'card'}, el('div', {class:'row spread'}, el('h2', {}, row.id), badge(row.alignment.status)),
    row.heading ? el('p', {class:'muted'}, row.heading) : null,
    row.context ? el('p', {class:'passage muted'}, row.context) : null, el('p', {class:'passage'}, row.authoritativeText),
    el('p', {class:'locator'}, locationText(row.sourceLocator)), el('h3', {}, 'Matching policy passages'),
    row.alignment.matches.length ? row.alignment.matches.map(match => el('article', {class:'card'},
      el('div', {class:'row spread'}, el('strong', {}, match.documentName), badge(match.status)),
      el('p', {class:'locator'}, locationText(match.locator)), highlighted(match.excerpt, match.matchedSpans),
      match.cautions.map(caution => el('p', {class:'note warning'}, caution)),
      button('Read extracted document', async () => {
        const doc = await json('/api/document?' + params({document:match.documentId})); showDocument(container, doc);
      }, 'quiet'))) : el('p', {class:'muted'}, row.alignment.searchComplete ? 'No matching passage was found in the selected documents.' : 'Some text could not be checked. Review the document read statuses.'),
    report.mappings.filter(edge => edge.source === row.id || edge.target === row.id).map(edge => el('p', {class:'note'}, `${edge.source} → ${edge.target}: ${edge.relationship}`))));
  container.scrollIntoView({block:'start'});
}
function renderDocuments(container, report) {
  const detail = el('div', {class:'details'});
  container.append(el('section', {class:'card table-wrap'}, el('h2', {}, 'Documents used in this run'), el('table', {},
    el('thead', {}, el('tr', {}, ['Document', 'Read status', 'Document status', ''].map(label => el('th', {}, label)))),
    el('tbody', {}, report.documents.map(doc => el('tr', {}, el('td', {}, doc.name), el('td', {}, doc.status), el('td', {}, doc.approvalStatus),
      el('td', {}, button('Read text', async () => showDocument(detail, await json('/api/document?' + params({document:doc.id}))), 'secondary'))))))), detail);
}
function showDocument(container, doc) {
  const passages = el('div'); let count = 0;
  const more = button('Show more passages', append, 'secondary');
  function append() {
    passages.append(...doc.passages.slice(count, count + 100).map(passage => el('article', {class:'card'},
      el('p', {class:'locator'}, locationText(passage.locator)), el('p', {class:'passage'}, passage.text))));
    count += 100; more.hidden = count >= doc.passages.length;
  }
  container.replaceChildren(el('section', {class:'card'}, el('h2', {}, doc.name),
    el('p', {class:'muted'}, `${doc.status} · ${doc.passages.length.toLocaleString()} retained passages`),
    doc.warnings.map(message => el('p', {class:'note warning'}, message)),
    el('p', {class:'locator'}, `SHA-256: ${doc.sha256}`), passages, more));
  append(); container.scrollIntoView({block:'start'});
}
function renderReports(container, report) {
  const choices = el('div', {class:'checks'}, report.versions.frameworks.map(fw => checkbox(fw.title, true, fw.edition, {name:'framework', value:fw.id})));
  const format = select([['html','HTML — readable in any browser'], ['csv','CSV — spreadsheet'], ['markdown','Markdown — text report'], ['json','JSON — structured data']], 'html', {'aria-label':'Report format'});
  const full = checkbox('Include matching policy passages', true, 'Turn this off for a summary without excerpts.');
  container.append(el('section', {class:'card'}, el('h2', {}, 'Export a report'),
    el('p', {class:'muted'}, 'Choose the frameworks for this report. Browser downloads are saved using your normal browser settings.'), choices,
    el('div', {class:'stack actions'}, field('Format', format), full), button('Download report', async () => {
      const selected = selectedFrameworks(choices); if (!selected.length) throw new Error('Choose at least one framework.');
      const query = params({format:format.value, full:String($('input',full).checked)});
      selected.forEach(key => query.append('framework',key));
      await download('/api/export?' + query, 'PolicyCompass-report.' + (format.value === 'markdown' ? 'md' : format.value));
    }), el('p', {class:'note actions'}, 'The report uses the run currently open, including when you have selected an earlier run in History.')));
}
function renderSettings() {
  main.append(...heading('Settings & help', 'Set defaults for new comparisons and see where this workspace keeps its files.'));
  const settings = state.status.settings;
  const organisation = el('input', {value:settings.organisation, maxlength:'500'});
  const choices = frameworkChecks(settings.frameworks);
  const maturity = maturityField(settings.ismMaturity);
  const retention = select([['extracted','All extracted text'], ['evidence','Matching passages only']], settings.retention);
  main.append(el('div', {class:'grid'}, el('section', {class:'card'}, el('h2', {}, 'Defaults'),
    field('Organisation', organisation), el('h3', {class:'actions'}, 'Preferred frameworks'), choices,
    el('div', {class:'stack actions'}, maturity, field('Keep text in saved comparisons', retention)),
    el('div', {class:'actions'}, button('Save settings', async () => {
      const frameworks = selectedFrameworks(choices); if (!frameworks.length) throw new Error('Choose at least one preferred framework.');
      state.status.settings = await json('/api/settings', {organisation:organisation.value, frameworks,
        ismMaturity:frameworks.includes('ism') ? $('select',maturity).value : '', retention:retention.value}); notice('Settings saved.');
    }))), el('section', {class:'card'}, el('h2', {}, 'Using the local workspace'),
      el('p', {}, 'Open PolicyCompass from its shortcut. It opens your browser and reuses a running instance. No account, terminal command or separate Python installation is needed.'),
      el('h3', {}, 'Files and privacy'), el('p', {}, 'Selected files are sent only to this computer. Temporary originals are removed after the operation. Saved comparisons keep extracted text and framework wording; they are not encrypted by the app.'),
      el('p', {}, 'Use Download comparison to back up or share a .policycompass file. Uninstalling the application leaves your comparisons and framework cache in place.'),
      el('h3', {}, 'Closing the app'), el('p', {}, 'Use Quit PolicyCompass to stop the local service. Closing every browser tab leaves it available for ten minutes, then it stops once any active work finishes.'),
      el('h3', {}, 'If a file cannot be read'), el('p', {}, 'Scanned PDFs need text recognition first. Password-protected, unsupported or oversized documents may not be read. Check the Documents tab before relying on unmatched results.'),
      el('h3', {}, 'Local workspace folder'), el('code', {}, state.status.home),
      el('p', {class:'muted actions'}, `Version ${state.status.version} · Windows 64-bit · unsigned pilot`))));
}

document.querySelectorAll('[data-page]').forEach(node => node.addEventListener('click', guarded(() => {
  if (node.dataset.page === 'new') state.appendId = null;
  notice(''); return showPage(node.dataset.page);
})));
$('.brand').addEventListener('click', guarded(event => {event.preventDefault();state.appendId=null;return showPage('new');}));
$('#cancel').addEventListener('click', guarded(async () => { const reply = await json('/api/cancel', {}); notice(reply.message); }));
$('#quit').addEventListener('click', guarded(async () => {
  if (state.busy && !window.confirm('Stop the current operation and quit PolicyCompass? Previously saved comparisons will be kept.')) return;
  const reply = await json('/api/quit', {}); state.quit = true;
  $('#job').hidden = true; notice('');
  document.querySelectorAll('button').forEach(node => {node.disabled=true;});
  main.replaceChildren(...heading('PolicyCompass is closing', reply.message), el('p', {}, 'Use the PolicyCompass shortcut when you want to open it again.'));
}));
guarded(async () => {
  if (!session) throw new Error('Open PolicyCompass using its shortcut to start a browser session.');
  await refreshStatus();
  if (!state.comparison) await showPage('new');
  poll();
})();
