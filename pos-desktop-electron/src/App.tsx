import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';
import {
  type CartLine,
  type FloorArea,
  type MenuItem,
  type RestaurantOrder,
  type User,
  formatMoney,
  getPosApi,
} from './pos-api';

type Tab = 'tables' | 'order' | 'kitchen' | 'quick' | 'inventory' | 'settings';

function App() {
  const api = useMemo(() => getPosApi(), []);
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [tab, setTab] = useState<Tab>('tables');

  const [mongoOk, setMongoOk] = useState<boolean | null>(null);
  const [mongoUri, setMongoUri] = useState('');
  const [configMsg, setConfigMsg] = useState<string | null>(null);

  const [floor, setFloor] = useState<FloorArea[]>([]);
  const [menu, setMenu] = useState<MenuItem[]>([]);

  const [selectedTableLabel, setSelectedTableLabel] = useState<string | null>(null);
  const [activeOrder, setActiveOrder] = useState<RestaurantOrder | null>(null);

  const [orderMsg, setOrderMsg] = useState<string | null>(null);
  const [kitchenOrders, setKitchenOrders] = useState<RestaurantOrder[]>([]);

  const [quickCart, setQuickCart] = useState<CartLine[]>([]);
  const [quickMsg, setQuickMsg] = useState<string | null>(null);

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);

  const refreshHealth = useCallback(async () => {
    if (!api) return;
    const h = await api.health();
    setMongoOk(h.ok === true && h.connected === true);
  }, [api]);

  const refreshFloor = useCallback(async () => {
    if (!api) return;
    setFloor(await api.listFloor());
  }, [api]);

  const refreshMenu = useCallback(async () => {
    if (!api) return;
    setMenu(await api.listMenu());
  }, [api]);

  const refreshKitchen = useCallback(async () => {
    if (!api) return;
    setKitchenOrders(await api.kitchenQueue());
  }, [api]);

  useEffect(() => {
    if (!api) {
      setBooting(false);
      return;
    }
    void (async () => {
      await refreshHealth();
      const cfg = await api.getConfig();
      setMongoUri(cfg.mongoUri);
      const session = await api.session();
      setUser(session);
      if (session) {
        await refreshMenu();
        await refreshFloor();
      }
      setBooting(false);
    })();
  }, [api, refreshFloor, refreshHealth, refreshMenu]);

  useEffect(() => {
    if (!api || !user || tab !== 'kitchen') return;
    void refreshKitchen();
    const id = window.setInterval(() => void refreshKitchen(), 8000);
    return () => window.clearInterval(id);
  }, [api, refreshKitchen, tab, user]);

  const loadActiveOrder = useCallback(
    async (orderId: string) => {
      if (!api) return;
      const o = await api.getOrder(orderId);
      setActiveOrder(o);
    },
    [api],
  );

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!api) return;
    setLoginError(null);
    const res = await api.login(username.trim(), password);
    if (!res.ok) {
      setLoginError(res.error);
      return;
    }
    setUser(res.user);
    setPassword('');
    await refreshHealth();
    await refreshMenu();
    await refreshFloor();
  };

  const onLogout = async () => {
    if (!api) return;
    await api.logout();
    setUser(null);
    setFloor([]);
    setMenu([]);
    setActiveOrder(null);
    setSelectedTableLabel(null);
    setTab('tables');
    setQuickCart([]);
  };

  const onSaveMongo = async () => {
    if (!api) return;
    setConfigMsg(null);
    const res = await api.setMongoUri(mongoUri.trim());
    if (!res.ok) {
      setConfigMsg(res.error);
      setMongoOk(false);
      return;
    }
    setConfigMsg('Connected.');
    await refreshHealth();
    await refreshMenu();
    await refreshFloor();
  };

  const selectTable = async (tableId: string, label: string) => {
    if (!api) return;
    setOrderMsg(null);
    const res = await api.startOrOpenForTable(tableId);
    if (!res.ok) {
      setOrderMsg(res.error);
      return;
    }
    setSelectedTableLabel(label);
    setActiveOrder(res.order);
    setTab('order');
  };

  const addMenuToOrder = async (item: MenuItem) => {
    if (!api || !activeOrder) return;
    setOrderMsg(null);
    const res = await api.addOrderLines(activeOrder.id, [{ menuItemId: item.id, qty: 1 }]);
    if (!res.ok) {
      setOrderMsg(res.error);
      return;
    }
    setActiveOrder(res.order);
    void refreshMenu();
  };

  const onSendKot = async () => {
    if (!api || !activeOrder) return;
    setOrderMsg(null);
    const res = await api.sendKot(activeOrder.id);
    if (!res.ok) {
      setOrderMsg(res.error);
      return;
    }
    setActiveOrder(res.order);
    setOrderMsg('KOT sent to kitchen.');
  };

  const onCompleteTableOrder = async () => {
    if (!api || !activeOrder) return;
    setOrderMsg(null);
    const res = await api.completeOrder(activeOrder.id);
    if (!res.ok) {
      setOrderMsg(res.error);
      return;
    }
    setOrderMsg(`Closed — ${formatMoney(res.totalCents)}`);
    setActiveOrder(null);
    setSelectedTableLabel(null);
    await refreshFloor();
    await refreshMenu();
    setTab('tables');
  };

  const quickTotal = useMemo(
    () => quickCart.reduce((s, l) => s + l.qty * l.unitPriceCents, 0),
    [quickCart],
  );

  const addQuick = (item: MenuItem) => {
    setQuickMsg(null);
    setQuickCart((prev) => {
      const i = prev.findIndex((x) => x.menuItemId === item.id);
      if (i === -1) {
        return [
          ...prev,
          { menuItemId: item.id, name: item.name, unitPriceCents: item.price_cents, qty: 1 },
        ];
      }
      const next = [...prev];
      const line = next[i];
      if (!line) return prev;
      if (line.qty >= item.stock) return prev;
      next[i] = { ...line, qty: line.qty + 1 };
      return next;
    });
  };

  const decQuick = (menuItemId: string) => {
    setQuickCart((prev) => {
      const i = prev.findIndex((x) => x.menuItemId === menuItemId);
      if (i === -1) return prev;
      const line = prev[i];
      if (!line) return prev;
      if (line.qty <= 1) return prev.filter((x) => x.menuItemId !== menuItemId);
      const next = [...prev];
      next[i] = { ...line, qty: line.qty - 1 };
      return next;
    });
  };

  const onQuickCheckout = async () => {
    if (!api || quickCart.length === 0) return;
    setQuickMsg(null);
    const res = await api.createWalkIn(
      quickCart.map((l) => ({ menuItemId: l.menuItemId, qty: l.qty })),
    );
    if (!res.ok) {
      setQuickMsg(res.error);
      return;
    }
    setQuickMsg(`Receipt OK — ${formatMoney(res.totalCents)} (#${res.orderId.slice(-6)})`);
    setQuickCart([]);
    await refreshMenu();
  };

  const kotBadgeClass = (s: string) => {
    if (s === 'pending') return 'kot-pending';
    if (s === 'sent') return 'kot-sent';
    if (s === 'preparing') return 'kot-prep';
    if (s === 'ready') return 'kot-ready';
    if (s === 'served') return 'kot-served';
    return '';
  };

  if (!api) {
    return (
      <div className="shell">
        <header className="topbar">
          <div className="brand">Restaurant POS</div>
        </header>
        <main className="main empty-state">
          <h1>Electron required</h1>
          <p>
            Run:
            <code className="code">npm run electron:dev</code>
          </p>
        </main>
      </div>
    );
  }

  if (booting) {
    return (
      <div className="shell center">
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="shell login-shell">
        <div className="login-card">
          <h1 className="login-title">Restaurant POS</h1>
          <p className="muted login-hint">MongoDB local/LAN · default user admin / admin123</p>
          <form className="login-form" onSubmit={onLogin}>
            <label className="field">
              <span>Username</span>
              <input
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {loginError ? <p className="error">{loginError}</p> : null}
            <button className="btn primary" type="submit">
              Sign in
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      {mongoOk === false ? (
        <div className="banner warn">
          MongoDB connect nahi ho raha. <strong>Settings</strong> mein URI check karo (local{' '}
          <code className="inline-code">127.0.0.1</code> ya LAN IP).
        </div>
      ) : null}

      <header className="topbar">
        <div className="brand">Restaurant POS</div>
        <nav className="nav">
          {(
            [
              ['tables', 'Tables'],
              ['order', 'Table order'],
              ['kitchen', 'Kitchen'],
              ['quick', 'Quick sale'],
              ['inventory', 'Menu'],
              ['settings', 'Settings'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={tab === id ? 'nav-btn active' : 'nav-btn'}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="user-area">
          <span className={`mongo-dot ${mongoOk ? 'ok' : 'bad'}`} title="MongoDB" />
          <span className="muted">
            {user.username} · {user.role}
          </span>
          <button type="button" className="btn ghost" onClick={() => void onLogout()}>
            Log out
          </button>
        </div>
      </header>

      <main className="main">
        {tab === 'tables' ? (
          <div className="panel">
            <div className="panel-head">
              <h2>Floor & tables</h2>
              <button type="button" className="btn ghost sm" onClick={() => void refreshFloor()}>
                Refresh
              </button>
            </div>
            {floor.length === 0 ? (
              <p className="muted">No floor data (Mongo connected?)</p>
            ) : (
              floor.map((a) => (
                <section key={a.id} className="floor-block">
                  <h3 className="floor-title">{a.name}</h3>
                  <div className="table-grid">
                    {a.tables.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        className={`table-tile ${t.status === 'occupied' ? 'occupied' : 'free'}`}
                        onClick={() => void selectTable(t.id, `${a.name} · ${t.name}`)}
                      >
                        <span className="table-name">{t.name}</span>
                        <span className="table-meta">{t.status}</span>
                      </button>
                    ))}
                  </div>
                </section>
              ))
            )}
          </div>
        ) : null}

        {tab === 'order' ? (
          <div className="grid-two">
            <section className="panel">
              <div className="panel-head">
                <h2>Menu</h2>
                <span className="muted small">
                  {selectedTableLabel ?? 'No table'} · order #{activeOrder?.id.slice(-6) ?? '—'}
                </span>
              </div>
              {!activeOrder ? (
                <p className="muted">Pehle Tables se table select karo.</p>
              ) : (
                <div className="product-list">
                  {menu.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="product-row"
                      disabled={item.stock <= 0}
                      onClick={() => void addMenuToOrder(item)}
                    >
                      <div>
                        <div className="product-name">{item.name}</div>
                        <div className="muted small">
                          {item.kitchenSection ?? '—'} · stock {item.stock}
                        </div>
                      </div>
                      <div className="product-price">{formatMoney(item.price_cents)}</div>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panel-head">
                <h2>Active order</h2>
                <div className="row-actions">
                  <button
                    type="button"
                    className="btn ghost sm"
                    disabled={!activeOrder}
                    onClick={() => void refreshMenu()}
                  >
                    Refresh menu
                  </button>
                </div>
              </div>
              {orderMsg ? <p className="success">{orderMsg}</p> : null}
              {!activeOrder ? (
                <p className="muted">Koi open order nahi.</p>
              ) : (
                <>
                  <table className="table compact">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th className="num">Qty</th>
                        <th className="num">KOT</th>
                        <th className="num">Line</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeOrder.lines.map((l) => (
                        <tr key={l.lineId}>
                          <td>{l.nameSnapshot}</td>
                          <td className="num">{l.qty}</td>
                          <td className="num">
                            <span className={`kot-tag ${kotBadgeClass(l.kotStatus)}`}>
                              {l.kotStatus}
                            </span>
                          </td>
                          <td className="num">{formatMoney(l.qty * l.unitPriceCents)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="cart-footer">
                    <div className="total">
                      <span>Subtotal</span>
                      <strong>{formatMoney(activeOrder.subtotalCents)}</strong>
                    </div>
                    <div className="row-actions wrap">
                      <button type="button" className="btn primary" onClick={() => void onSendKot()}>
                        Send KOT
                      </button>
                      <button
                        type="button"
                        className="btn"
                        onClick={() => void onCompleteTableOrder()}
                      >
                        Complete &amp; pay
                      </button>
                      <button
                        type="button"
                        className="btn ghost"
                        onClick={() => void loadActiveOrder(activeOrder.id)}
                      >
                        Reload order
                      </button>
                    </div>
                  </div>
                </>
              )}
            </section>
          </div>
        ) : null}

        {tab === 'kitchen' ? (
          <div className="panel">
            <div className="panel-head">
              <h2>Kitchen queue</h2>
              <button type="button" className="btn ghost sm" onClick={() => void refreshKitchen()}>
                Refresh now
              </button>
            </div>
            {kitchenOrders.length === 0 ? (
              <p className="muted">Abhi kitchen ko koi pending ticket nahi.</p>
            ) : (
              kitchenOrders.map((o) => (
                <div key={o.id} className="kot-card">
                  <div className="kot-head">
                    <strong>
                      Order #{o.id.slice(-6)} · {o.orderType}
                    </strong>
                    <span className="muted small">
                      Table {o.tableId ? o.tableId.slice(-4) : '—'}
                    </span>
                  </div>
                  <ul className="kot-lines">
                    {o.lines
                      .filter((l) => ['sent', 'preparing', 'ready'].includes(l.kotStatus))
                      .map((l) => (
                        <li key={l.lineId} className="kot-line">
                          <div>
                            <span className="qty">{l.qty}×</span> {l.nameSnapshot}
                            <span className={`kot-tag ${kotBadgeClass(l.kotStatus)}`}>
                              {l.kotStatus}
                            </span>
                          </div>
                          <div className="kot-btns">
                            <button
                              type="button"
                              className="btn ghost sm"
                              onClick={() =>
                                api?.kitchenUpdateLine(o.id, l.lineId, 'preparing').then((r) => {
                                  if (r.ok) void refreshKitchen();
                                })
                              }
                            >
                              Prep
                            </button>
                            <button
                              type="button"
                              className="btn ghost sm"
                              onClick={() =>
                                api?.kitchenUpdateLine(o.id, l.lineId, 'ready').then((r) => {
                                  if (r.ok) void refreshKitchen();
                                })
                              }
                            >
                              Ready
                            </button>
                            <button
                              type="button"
                              className="btn ghost sm"
                              onClick={() =>
                                api?.kitchenUpdateLine(o.id, l.lineId, 'served').then((r) => {
                                  if (r.ok) void refreshKitchen();
                                })
                              }
                            >
                              Served
                            </button>
                          </div>
                        </li>
                      ))}
                  </ul>
                </div>
              ))
            )}
          </div>
        ) : null}

        {tab === 'quick' ? (
          <div className="grid-two">
            <section className="panel">
              <div className="panel-head">
                <h2>Walk-in / takeaway</h2>
              </div>
              <div className="product-list">
                {menu.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="product-row"
                    disabled={item.stock <= 0}
                    onClick={() => addQuick(item)}
                  >
                    <div>
                      <div className="product-name">{item.name}</div>
                      <div className="muted small">stock {item.stock}</div>
                    </div>
                    <div className="product-price">{formatMoney(item.price_cents)}</div>
                  </button>
                ))}
              </div>
            </section>
            <section className="panel">
              <div className="panel-head">
                <h2>Cart</h2>
                <button type="button" className="btn ghost sm" onClick={() => setQuickCart([])}>
                  Clear
                </button>
              </div>
              {quickMsg ? <p className="success">{quickMsg}</p> : null}
              {quickCart.length === 0 ? (
                <p className="muted">Items select karo.</p>
              ) : (
                <ul className="cart">
                  {quickCart.map((l) => (
                    <li key={l.menuItemId} className="cart-line">
                      <div>
                        <div className="product-name">{l.name}</div>
                        <div className="muted small">{formatMoney(l.unitPriceCents)} each</div>
                      </div>
                      <div className="cart-controls">
                        <button
                          type="button"
                          className="btn ghost sm"
                          onClick={() => decQuick(l.menuItemId)}
                        >
                          −
                        </button>
                        <span className="qty">{l.qty}</span>
                        <button
                          type="button"
                          className="btn ghost sm"
                          onClick={() => {
                            const stock = menu.find((m) => m.id === l.menuItemId)?.stock ?? 0;
                            if (l.qty >= stock) return;
                            setQuickCart((prev) =>
                              prev.map((x) =>
                                x.menuItemId === l.menuItemId ? { ...x, qty: x.qty + 1 } : x,
                              ),
                            );
                          }}
                        >
                          +
                        </button>
                        <span className="line-total">
                          {formatMoney(l.qty * l.unitPriceCents)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <div className="cart-footer">
                <div className="total">
                  <span>Total</span>
                  <strong>{formatMoney(quickTotal)}</strong>
                </div>
                <button
                  type="button"
                  className="btn primary"
                  disabled={quickCart.length === 0}
                  onClick={() => void onQuickCheckout()}
                >
                  Complete sale
                </button>
              </div>
            </section>
          </div>
        ) : null}

        {tab === 'inventory' ? (
          <section className="panel">
            <div className="panel-head">
              <h2>Menu (inventory view)</h2>
              <button type="button" className="btn ghost sm" onClick={() => void refreshMenu()}>
                Refresh
              </button>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>SKU</th>
                  <th>Kitchen</th>
                  <th className="num">Price</th>
                  <th className="num">Stock</th>
                </tr>
              </thead>
              <tbody>
                {menu.map((p) => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td className="muted">{p.sku ?? '—'}</td>
                    <td className="muted">{p.kitchenSection ?? '—'}</td>
                    <td className="num">{formatMoney(p.price_cents)}</td>
                    <td className="num">{p.stock}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}

        {tab === 'settings' ? (
          <section className="panel narrow">
            <h2>MongoDB connection</h2>
            <p className="muted small">
              Same PC: <code className="inline-code">mongodb://127.0.0.1:27017/offline_pos</code>
              <br />
              LAN server: <code className="inline-code">mongodb://192.168.x.x:27017/offline_pos</code>
            </p>
            <label className="field">
              <span>MONGODB_URI</span>
              <input value={mongoUri} onChange={(e) => setMongoUri(e.target.value)} />
            </label>
            {configMsg ? (
              <p className={configMsg.startsWith('Connected') ? 'success' : 'error'}>{configMsg}</p>
            ) : null}
            <button type="button" className="btn primary" onClick={() => void onSaveMongo()}>
              Save &amp; reconnect
            </button>
            <button
              type="button"
              className="btn ghost"
              style={{ marginLeft: 8 }}
              onClick={() => void refreshHealth()}
            >
              Check health
            </button>
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default App;
