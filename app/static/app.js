const CURRENCY = 'BDT';
const cart = new Map();
const state = { user: null, menu: [], tables: [], orders: [], reservations: [], inventory: [], staff: [], recipeItemId: null };
const views = ['dashboard', 'orders', 'reservations', 'menu', 'inventory'];
const byId = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat('en-BD', { style: 'currency', currency: CURRENCY, maximumFractionDigits: 2 }).format(Number(value || 0));
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

function toast(message, kind = 'success') {
  const node = document.createElement('div');
  node.className = `toast ${kind === 'error' ? 'error' : kind === 'warning' ? 'warning' : ''}`;
  node.textContent = message;
  byId('toast-region').append(node);
  window.setTimeout(() => node.remove(), 4500);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = localStorage.getItem('restaurantToken');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch (_) {
    throw new Error('Could not reach the server. Check your connection and try again.');
  }
  if (response.status === 401 && path !== '/auth/login') {
    localStorage.removeItem('restaurantToken');
    showLogin();
    throw new Error('Your session ended. Please sign in again.');
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') detail = payload.detail;
      else if (Array.isArray(payload.detail)) detail = payload.detail.map((e) => e.msg).join(', ');
    } catch (_) { /* Keep the status message for non-JSON errors. */ }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showLogin() {
  state.user = null;
  byId('app-shell').classList.add('hidden');
  byId('login-screen').classList.remove('hidden');
}

function showApp(user) {
  state.user = user;
  byId('login-screen').classList.add('hidden');
  byId('app-shell').classList.remove('hidden');
  byId('user-label').textContent = user.username;
  byId('role-label').textContent = user.role;
  byId('avatar-initial').textContent = (user.username || 'R').slice(0, 1).toUpperCase();
  byId('welcome-title').textContent = `Welcome, ${user.username}`;
  byId('today-label').textContent = new Intl.DateTimeFormat('en-BD', { dateStyle: 'medium' }).format(new Date());
  const isAdmin = user.role === 'admin';
  byId('menu-admin-panel').classList.toggle('hidden', !isAdmin);
  byId('inventory-admin-panel').classList.toggle('hidden', !isAdmin);
  byId('staff-admin-panel').classList.toggle('hidden', !isAdmin);
  loadWorkspace();
}

function navigate(view) {
  if (!views.includes(view)) return;
  document.querySelectorAll('.view').forEach((node) => node.classList.toggle('active', node.id === `view-${view}`));
  document.querySelectorAll('[data-view-link]').forEach((node) => node.classList.toggle('active', node.dataset.viewLink === view));
  const labels = { dashboard: 'Overview', orders: 'Orders', reservations: 'Reservations', menu: 'Menu', inventory: 'Inventory' };
  byId('page-crumb').textContent = labels[view];
  byId('sidebar').classList.remove('open');
  if (view === 'orders') renderCart();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function statusBadge(status) {
  return `<span class="status-badge status-${esc(status)}">${esc(status)}</span>`;
}

function emptyState(title, detail) {
  return `<div class="empty-state"><strong>${esc(title)}</strong>${esc(detail)}</div>`;
}

function fillCategories(selectId, items, selected = '') {
  const select = byId(selectId);
  if (!select) return;
  const categories = [...new Set(items.map((item) => item.category).filter(Boolean))].sort();
  select.innerHTML = '<option value="">All categories</option>' + categories.map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
  select.value = categories.includes(selected) ? selected : '';
}

function renderMenuBuilder() {
  const search = (byId('menu-search').value || '').trim().toLowerCase();
  const category = byId('menu-category').value;
  const items = state.menu.filter((item) => item.is_available && (!category || item.category === category) && `${item.name} ${item.description || ''}`.toLowerCase().includes(search));
  byId('menu-item-count').textContent = `${items.length} ${items.length === 1 ? 'item' : 'items'}`;
  byId('menu-grid').innerHTML = items.length ? items.map((item) => `<article class="menu-item"><div class="menu-item-top"><h3>${esc(item.name)}</h3></div><p>${esc(item.description || 'Freshly prepared to order.')}</p><div class="menu-item-bottom"><span class="menu-price">${money(item.price)}</span><button class="add-item" data-add-item="${item.id}" aria-label="Add ${esc(item.name)} to order">＋</button></div></article>`).join('') : emptyState('No menu items found', 'Try another search or category.');
}

function renderCart() {
  const chosen = [...cart.entries()].map(([id, quantity]) => ({ item: state.menu.find((menuItem) => menuItem.id === id), quantity })).filter((line) => line.item);
  byId('cart-lines').innerHTML = chosen.length ? chosen.map(({ item, quantity }) => `<div class="cart-line"><div><div class="cart-line-name">${esc(item.name)}</div><div class="cart-line-meta">${money(item.price)} each · ${money(item.price * quantity)}</div></div><div class="quantity-control"><button data-cart-step="-1" data-item-id="${item.id}" aria-label="Remove one ${esc(item.name)}">−</button><strong>${quantity}</strong><button data-cart-step="1" data-item-id="${item.id}" aria-label="Add one ${esc(item.name)}">＋</button></div></div>`).join('') : '<div class="empty-inline">Your order is empty. Add an item to get started.</div>';
  const total = chosen.reduce((sum, line) => sum + Number(line.item.price) * line.quantity, 0);
  byId('cart-total').textContent = money(total);
  byId('place-order').disabled = !chosen.length;
}

function renderOrders(orders, compact = false) {
  if (!orders.length) return emptyState('No orders yet', 'New orders will appear here as soon as they are placed.');
  const rows = orders.map((order) => {
    const names = order.items.map((line) => {
      const item = state.menu.find((menuItem) => menuItem.id === line.menu_item_id);
      return `${line.quantity}× ${esc(item?.name || `Menu item ${line.menu_item_id}`)}`;
    }).join(', ');
    const next = { pending: 'preparing', preparing: 'served', served: 'paid' }[order.status];
    const actions = next ? `<button class="table-action" data-order-status="${next}" data-order-id="${order.id}">Mark ${next}</button>${['pending', 'preparing'].includes(order.status) ? ` <button class="table-action danger" data-order-status="cancelled" data-order-id="${order.id}">Cancel</button>` : ''}` : '—';
    const table = state.tables.find((entry) => entry.id === order.table_id);
    const destination = table ? `Table ${table.number}` : order.table_id ? `Table ${order.table_id}` : 'Takeaway';
    return `<tr><td>#${order.id}</td><td>${new Date(order.created_at).toLocaleString('en-BD', { dateStyle: 'short', timeStyle: 'short' })}</td><td>${destination}</td><td>${names || '—'}</td><td>${money(order.total_amount)}</td><td>${statusBadge(order.status)}</td>${compact ? '' : `<td>${actions}</td>`}</tr>`;
  }).join('');
  return `<table class="data-table"><thead><tr><th>Ticket</th><th>Time</th><th>Table</th><th>Items</th><th>Total</th><th>Status</th>${compact ? '' : '<th>Action</th>'}</tr></thead><tbody>${rows}</tbody></table>`;
}

function renderReservations() {
  const filter = byId('reservation-filter').value;
  const reservations = state.reservations.filter((item) => !filter || item.status === filter);
  if (!reservations.length) return emptyState('No reservations to show', 'Bookings will appear here once they are created.');
  const rows = reservations.map((item) => { const table = state.tables.find((entry) => entry.id === item.table_id); return `<tr><td>${esc(item.customer_name)}${item.phone ? `<br><span class="muted">${esc(item.phone)}</span>` : ''}</td><td>${item.party_size}</td><td>Table ${table?.number ?? item.table_id}</td><td>${new Date(item.start_time).toLocaleString('en-BD', { dateStyle: 'medium', timeStyle: 'short' })}<br><span class="muted">Until ${new Date(item.end_time).toLocaleTimeString('en-BD', { timeStyle: 'short' })}</span></td><td>${statusBadge(item.status)}</td><td>${item.status === 'confirmed' ? `<button class="table-action danger" data-cancel-reservation="${item.id}">Cancel</button>` : '—'}</td></tr>`; }).join('');
  return `<table class="data-table"><thead><tr><th>Guest</th><th>Party</th><th>Table</th><th>Time</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderCatalog() {
  const search = (byId('catalog-search').value || '').trim().toLowerCase();
  const category = byId('catalog-category').value;
  const items = state.menu.filter((item) => (!category || item.category === category) && `${item.name} ${item.description || ''}`.toLowerCase().includes(search));
  byId('catalog-count').textContent = `${items.length} ${items.length === 1 ? 'item' : 'items'}`;
  byId('catalog-grid').innerHTML = items.length ? items.map((item) => `<article class="catalog-card ${item.is_available ? '' : 'is-unavailable'}"><span class="category-label">${esc(item.category)}</span><h3>${esc(item.name)}</h3><p>${esc(item.description || 'No description added.')}</p><div class="catalog-card-bottom"><span class="menu-price">${money(item.price)}</span><span class="availability ${item.is_available ? '' : 'off'}">${item.is_available ? 'Available' : 'Unavailable'}</span></div>${state.user.role === 'admin' ? `<div class="catalog-actions"><button class="table-action" data-edit-recipe="${item.id}">Recipe (${item.recipe?.length || 0})</button><button class="table-action" data-toggle-menu="${item.id}" data-available="${item.is_available}">${item.is_available ? 'Pause item' : 'Make available'}</button></div>` : ''}</article>`).join('') : emptyState('No menu items found', 'Try changing your search or category.');
}

function renderInventory() {
  const filter = byId('stock-filter').value;
  const items = state.inventory.filter((item) => filter === 'low' ? item.quantity <= item.reorder_level : filter === 'healthy' ? item.quantity > item.reorder_level : true);
  const lowCount = state.inventory.filter((item) => item.quantity <= item.reorder_level).length;
  byId('inventory-total').textContent = state.inventory.length;
  byId('inventory-low').textContent = lowCount;
  byId('inventory-low').className = lowCount ? 'stock-low' : 'stock-good';
  byId('inventory-tables').textContent = state.tables.filter((table) => table.is_active).length;
  byId('nav-stock-count').textContent = lowCount;
  byId('nav-stock-count').classList.toggle('hidden', !lowCount);
  byId('inventory-table').innerHTML = items.length ? `<table class="data-table"><thead><tr><th>Ingredient</th><th>In stock</th><th>Reorder at</th><th>Status</th><th>Restock</th></tr></thead><tbody>${items.map((item) => `<tr><td>${esc(item.name)}<br><span class="muted">${esc(item.unit)}</span></td><td>${Number(item.quantity).toLocaleString('en-BD')}</td><td>${Number(item.reorder_level).toLocaleString('en-BD')}</td><td>${item.quantity <= item.reorder_level ? '<span class="status-badge status-cancelled">Low stock</span>' : '<span class="status-badge status-completed">Healthy</span>'}</td><td><div class="restock-control"><input id="restock-${item.id}" type="number" min="0.01" step="any" placeholder="Amount" aria-label="Amount to restock ${esc(item.name)}"><button class="table-action" data-restock="${item.id}">Add</button></div></td></tr>`).join('')}</tbody></table>` : emptyState(filter === 'low' ? 'No low stock items' : 'No inventory items', filter === 'low' ? 'Your current stock is above reorder levels.' : 'Add ingredients to start tracking stock.');
  const alerts = state.inventory.filter((item) => item.quantity <= item.reorder_level);
  byId('dashboard-stock').innerHTML = alerts.length ? `<strong>${alerts.length} ingredient${alerts.length === 1 ? '' : 's'} need attention</strong><br>${alerts.slice(0, 3).map((item) => `${esc(item.name)} · ${Number(item.quantity).toLocaleString('en-BD')} ${esc(item.unit)} left`).join('<br>')}` : 'No low stock alerts. Inventory is looking healthy.';
}

function renderDashboard() {
  const activeOrders = state.orders.filter((order) => ['pending', 'preparing', 'served'].includes(order.status));
  const confirmed = state.reservations.filter((reservation) => reservation.status === 'confirmed');
  const low = state.inventory.filter((item) => item.quantity <= item.reorder_level);
  byId('metric-orders').textContent = activeOrders.length;
  byId('metric-reservations').textContent = confirmed.length;
  byId('metric-stock').textContent = low.length;
  byId('nav-order-count').textContent = activeOrders.length;
  byId('nav-order-count').classList.toggle('hidden', !activeOrders.length);
  if (state.user.role === 'admin') {
    byId('metric-sales').textContent = money(state.dailySales?.total_revenue || 0);
    byId('metric-sales-note').textContent = `${state.dailySales?.total_orders || 0} orders today`;
  } else {
    byId('metric-sales').textContent = '—';
    byId('metric-sales-note').textContent = 'Sales report available to admins';
  }
  byId('dashboard-orders').innerHTML = renderOrders(state.orders.slice(0, 5), true);
  byId('daily-highlights').innerHTML = state.user.role === 'admin' && state.dailySales
    ? `<div class="highlight-title">Today’s top items</div>${state.dailySales.top_items.length ? state.dailySales.top_items.slice(0, 3).map((item) => `<div class="highlight-row"><span>${esc(item.name)}</span><strong>${item.quantity_sold} sold</strong></div>`).join('') : '<div class="muted small-note">No sales recorded today.</div>'}`
    : '';
}

function renderAll() {
  fillCategories('menu-category', state.menu.filter((item) => item.is_available), byId('menu-category').value);
  fillCategories('catalog-category', state.menu, byId('catalog-category').value);
  renderMenuBuilder();
  renderCart();
  byId('orders-table').innerHTML = renderOrders(state.orders.filter((order) => !byId('order-filter').value || order.status === byId('order-filter').value));
  byId('reservations-table').innerHTML = renderReservations();
  renderCatalog();
  renderInventory();
  renderDashboard();
  fillTables();
  renderStaff();
}

function fillTables() {
  const active = state.tables.filter((table) => table.is_active).sort((a, b) => a.number - b.number);
  const options = active.map((table) => `<option value="${table.id}">Table ${table.number} · ${table.capacity} seats</option>`).join('');
  byId('order-table').innerHTML = '<option value="">Select a table or takeaway…</option><option value="takeaway">Takeaway / no table</option>' + options;
  byId('order-table-help').textContent = active.length
    ? 'Select the dining table that should receive this order, or choose takeaway.'
    : 'No dining tables are set up yet. Choose takeaway or ask an admin to add tables.';
  byId('reservation-table').innerHTML = '<option value="">Auto-assign best available</option>' + options;
}

function renderStaff() {
  byId('staff-list').innerHTML = state.staff.length ? state.staff.map((user) => `<span class="staff-chip">${esc(user.username)}</span>`).join('') : '<span class="muted">No staff accounts created yet.</span>';
}

async function loadWorkspace() {
  const tasks = [
    api('/menu?only_available=false').then((data) => { state.menu = data; }),
    api('/tables').then((data) => { state.tables = data; }),
    api('/orders').then((data) => { state.orders = data; }),
    api('/reservations').then((data) => { state.reservations = data; }),
    api('/inventory').then((data) => { state.inventory = data; }),
  ];
  if (state.user.role === 'admin') {
    tasks.push(api('/reports/daily-sales').then((data) => { state.dailySales = data; }).catch((error) => { state.dailySales = null; toast(error.message, 'error'); }));
    tasks.push(api('/auth/staff').then((data) => { state.staff = data; }).catch((error) => { state.staff = []; toast(error.message, 'error'); }));
  }
  const results = await Promise.allSettled(tasks);
  if (!state.user) { toast('Your session ended. Please sign in again.', 'warning'); return; }
  const rejected = results.find((result) => result.status === 'rejected');
  renderAll();
  if (rejected) toast(rejected.reason.message, 'error');
}

async function submitOrder() {
  const items = [...cart.entries()].map(([menu_item_id, quantity]) => ({ menu_item_id, quantity }));
  if (!items.length) return;
  const destination = byId('order-table').value;
  if (!destination) { toast('Choose a table or takeaway destination before sending the order.', 'warning'); byId('order-table').focus(); return; }
  byId('place-order').disabled = true;
  try {
    const order = await api('/orders', { method: 'POST', body: JSON.stringify({ table_id: destination === 'takeaway' ? null : Number(destination), notes: byId('order-notes').value.trim() || null, items }) });
    cart.clear();
    byId('order-notes').value = '';
    toast(`Order #${order.id} sent to the kitchen.`);
    await loadWorkspace();
  } catch (error) { toast(error.message, 'error'); renderCart(); }
}

async function updateOrder(id, status) {
  try { await api(`/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }); toast(`Order #${id} marked ${status}.`); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function submitReservation(event) {
  event.preventDefault();
  const reservationForm = event.currentTarget;
  const form = new FormData(reservationForm);
  const tableId = form.get('table_id');
  // The API stores local wall time in a timezone-naive DateTime column. Keep
  // the datetime-local value as-is instead of converting it to UTC.
  const payload = { customer_name: String(form.get('customer_name')).trim(), phone: String(form.get('phone') || '').trim() || null, party_size: Number(form.get('party_size')), duration_minutes: Number(form.get('duration_minutes')), start_time: String(form.get('start_time')), table_id: tableId ? Number(tableId) : null };
  try {
    const reservation = await api('/reservations', { method: 'POST', body: JSON.stringify(payload) });
    reservationForm.reset();
    const table = state.tables.find((entry) => entry.id === reservation.table_id);
    toast(`Reservation confirmed for Table ${table?.number ?? reservation.table_id}.`);
    await loadWorkspace();
  } catch (error) { toast(error.message, 'error'); }
}

async function cancelReservation(id) {
  try { await api(`/reservations/${id}`, { method: 'DELETE' }); toast('Reservation cancelled.'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function restock(id) {
  const input = byId(`restock-${id}`);
  const quantity = Number(input.value);
  if (!Number.isFinite(quantity) || quantity <= 0) { toast('Enter a restock amount greater than zero.', 'warning'); input.focus(); return; }
  try { await api(`/inventory/${id}/restock`, { method: 'PATCH', body: JSON.stringify({ quantity }) }); toast('Stock quantity updated.'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function createMenuItem(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = { name: byId('new-menu-name').value.trim(), description: byId('new-menu-description').value.trim() || null, price: Number(byId('new-menu-price').value), category: byId('new-menu-category').value.trim(), is_available: true };
  try { const item = await api('/menu', { method: 'POST', body: JSON.stringify(payload) }); form.reset(); byId('new-menu-category').value = 'main'; toast(`${item.name} added to the menu.`); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function createInventoryItem(event) {
  event.preventDefault();
  const formNode = event.currentTarget;
  const form = new FormData(formNode);
  const payload = { name: String(form.get('name')).trim(), unit: String(form.get('unit')).trim(), quantity: Number(form.get('quantity')), reorder_level: Number(form.get('reorder_level')) };
  try { await api('/inventory', { method: 'POST', body: JSON.stringify(payload) }); formNode.reset(); formNode.elements.unit.value = 'kg'; formNode.elements.quantity.value = '0'; formNode.elements.reorder_level.value = '0'; toast('Ingredient added to inventory.'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function createTable(event) {
  event.preventDefault();
  const formNode = event.currentTarget;
  const form = new FormData(event.currentTarget);
  const payload = { number: Number(form.get('number')), capacity: Number(form.get('capacity')) };
  try { await api('/tables', { method: 'POST', body: JSON.stringify(payload) }); formNode.reset(); toast('Dining table added.'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function createStaff(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = { username: byId('new-staff-username').value.trim(), password: byId('new-staff-password').value };
  try { await api('/auth/staff', { method: 'POST', body: JSON.stringify(payload) }); form.reset(); toast('Staff account created.'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

function addRecipeLine(ingredientId = '', quantity = '') {
  const options = state.inventory.map((item) => `<option value="${item.id}" ${Number(ingredientId) === item.id ? 'selected' : ''}>${esc(item.name)} (${esc(item.unit)})</option>`).join('');
  const row = document.createElement('div');
  row.className = 'recipe-line';
  row.innerHTML = `<select class="field-control recipe-ingredient"><option value="">Choose ingredient</option>${options}</select><input class="field-control recipe-quantity" type="number" min="0.0001" step="any" value="${esc(quantity)}" placeholder="Amount per portion" aria-label="Quantity per portion"><button class="recipe-remove" type="button" data-action="remove-recipe-line">Remove</button>`;
  byId('recipe-lines').append(row);
}

function openRecipe(id) {
  const item = state.menu.find((menuItem) => menuItem.id === id);
  if (!item) return;
  state.recipeItemId = id;
  byId('recipe-item-name').textContent = item.name;
  byId('recipe-lines').innerHTML = '';
  if (item.recipe?.length) item.recipe.forEach((line) => addRecipeLine(line.inventory_item_id, line.quantity_required));
  else addRecipeLine();
  byId('recipe-editor').classList.remove('hidden');
  byId('recipe-editor').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function saveRecipe() {
  const ingredients = [...document.querySelectorAll('.recipe-line')].map((row) => ({ inventory_item_id: Number(row.querySelector('.recipe-ingredient').value), quantity_required: Number(row.querySelector('.recipe-quantity').value) }));
  if (ingredients.some((item) => !item.inventory_item_id || !Number.isFinite(item.quantity_required) || item.quantity_required <= 0)) { toast('Choose an ingredient and enter a quantity for every recipe row.', 'warning'); return; }
  if (new Set(ingredients.map((item) => item.inventory_item_id)).size !== ingredients.length) { toast('Each ingredient can only appear once in a recipe.', 'warning'); return; }
  try { await api(`/menu/${state.recipeItemId}/recipe`, { method: 'PUT', body: JSON.stringify(ingredients) }); toast('Recipe saved. Orders will now update stock automatically.'); byId('recipe-editor').classList.add('hidden'); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function toggleMenuAvailability(id, isAvailable) {
  try { await api(`/menu/${id}`, { method: 'PATCH', body: JSON.stringify({ is_available: !isAvailable }) }); toast(`Menu item ${isAvailable ? 'paused' : 'made available'}.`); await loadWorkspace(); }
  catch (error) { toast(error.message, 'error'); }
}

async function login(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username: byId('login-username').value.trim(), password: byId('login-password').value }) });
    localStorage.setItem('restaurantToken', result.access_token);
    byId('login-password').value = '';
    showApp(result.user);
  } catch (error) { toast(error.message, 'error'); }
  finally { button.disabled = false; }
}

function logout() {
  localStorage.removeItem('restaurantToken');
  state.menu = []; state.tables = []; state.orders = []; state.reservations = []; state.inventory = []; state.staff = [];
  showLogin();
}

document.addEventListener('click', async (event) => {
  const viewLink = event.target.closest('[data-view-link]');
  if (viewLink) { event.preventDefault(); navigate(viewLink.dataset.viewLink); return; }
  const add = event.target.closest('[data-add-item]');
  if (add) { const id = Number(add.dataset.addItem); cart.set(id, (cart.get(id) || 0) + 1); renderCart(); return; }
  const step = event.target.closest('[data-cart-step]');
  if (step) { const id = Number(step.dataset.itemId); const quantity = (cart.get(id) || 0) + Number(step.dataset.cartStep); if (quantity > 0) cart.set(id, quantity); else cart.delete(id); renderCart(); return; }
  const orderStatus = event.target.closest('[data-order-status]');
  if (orderStatus) { await updateOrder(Number(orderStatus.dataset.orderId), orderStatus.dataset.orderStatus); return; }
  const cancel = event.target.closest('[data-cancel-reservation]');
  if (cancel) { await cancelReservation(Number(cancel.dataset.cancelReservation)); return; }
  const stockButton = event.target.closest('[data-restock]');
  if (stockButton) { await restock(Number(stockButton.dataset.restock)); return; }
  const recipe = event.target.closest('[data-edit-recipe]');
  if (recipe) { openRecipe(Number(recipe.dataset.editRecipe)); return; }
  const toggle = event.target.closest('[data-toggle-menu]');
  if (toggle) { await toggleMenuAvailability(Number(toggle.dataset.toggleMenu), toggle.dataset.available === 'true'); return; }
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action === 'refresh') { await loadWorkspace(); toast('Workspace refreshed.'); }
  if (action === 'add-recipe-line') addRecipeLine();
  if (action === 'remove-recipe-line') event.target.closest('.recipe-line').remove();
  if (action === 'close-recipe') byId('recipe-editor').classList.add('hidden');
});

byId('login-form').addEventListener('submit', login);
byId('logout-button').addEventListener('click', logout);
byId('place-order').addEventListener('click', submitOrder);
byId('clear-cart').addEventListener('click', () => { cart.clear(); renderCart(); });
byId('reservation-form').addEventListener('submit', submitReservation);
byId('menu-item-form').addEventListener('submit', createMenuItem);
byId('inventory-item-form').addEventListener('submit', createInventoryItem);
byId('table-item-form').addEventListener('submit', createTable);
byId('staff-form').addEventListener('submit', createStaff);
byId('save-recipe').addEventListener('click', saveRecipe);
byId('menu-search').addEventListener('input', renderMenuBuilder);
byId('menu-category').addEventListener('change', renderMenuBuilder);
byId('catalog-search').addEventListener('input', renderCatalog);
byId('catalog-category').addEventListener('change', renderCatalog);
  byId('order-filter').addEventListener('change', () => { byId('orders-table').innerHTML = renderOrders(state.orders.filter((order) => !byId('order-filter').value || order.status === byId('order-filter').value)); });
byId('reservation-filter').addEventListener('change', () => { byId('reservations-table').innerHTML = renderReservations(); });
byId('stock-filter').addEventListener('change', renderInventory);
byId('menu-toggle').addEventListener('click', () => byId('sidebar').classList.toggle('open'));

async function restoreSession() {
  const token = localStorage.getItem('restaurantToken');
  if (!token) { showLogin(); return; }
  try { showApp(await api('/auth/me')); }
  catch (_) { localStorage.removeItem('restaurantToken'); showLogin(); }
}

restoreSession();
