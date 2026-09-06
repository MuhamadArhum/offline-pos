const crypto = require('crypto');
const { ObjectId } = require('mongodb');
const { hashPassword } = require('./cryptoUtil.cjs');
const { loadConfig, saveConfig } = require('./configStore.cjs');

function safeUser(doc) {
  if (!doc) return null;
  return { id: doc._id.toString(), username: doc.username, role: doc.role };
}

function safeMenuItem(doc) {
  return {
    id: doc._id.toString(),
    name: doc.name,
    sku: doc.sku != null ? String(doc.sku) : null,
    price_cents: doc.priceCents,
    stock: doc.stock,
    kitchenSection: doc.kitchenSection != null ? String(doc.kitchenSection) : null,
  };
}

function safeLine(line) {
  return {
    lineId: line.lineId,
    menuItemId: line.menuItemId.toString(),
    nameSnapshot: line.nameSnapshot,
    qty: line.qty,
    unitPriceCents: line.unitPriceCents,
    kotStatus: line.kotStatus,
  };
}

function safeOrder(doc) {
  if (!doc) return null;
  return {
    id: doc._id.toString(),
    orderType: doc.orderType,
    tableId: doc.tableId ? doc.tableId.toString() : null,
    status: doc.status,
    lines: (doc.lines || []).map(safeLine),
    subtotalCents: doc.subtotalCents ?? 0,
    totalCents: doc.totalCents ?? 0,
    createdAt: doc.createdAt,
    updatedAt: doc.updatedAt,
  };
}

function totalsFromLines(lines) {
  const subtotalCents = lines.reduce((s, l) => s + l.qty * l.unitPriceCents, 0);
  return { subtotalCents, totalCents: subtotalCents };
}

function registerIpc(ipcMain, ctx) {
  const {
    app,
    mongoHub,
    getConnectionError,
    setConnectionError,
    getUser,
    setUser,
  } = ctx;

  async function withDb(fn) {
    if (!mongoHub.isConnected()) {
      throw new Error(getConnectionError() || 'MongoDB not connected');
    }
    const db = mongoHub.getDb();
    return fn(db);
  }

  ipcMain.handle('system:health', async () => {
    try {
      await withDb(async (db) => {
        await db.command({ ping: 1 });
      });
      return { ok: true, connected: true };
    } catch (e) {
      return {
        ok: false,
        connected: false,
        error: e instanceof Error ? e.message : String(e),
      };
    }
  });

  ipcMain.handle('config:get', async () => {
    const cfg = loadConfig(app);
    return { mongoUri: cfg.mongoUri };
  });

  ipcMain.handle('config:setMongoUri', async (_e, mongoUri) => {
    if (typeof mongoUri !== 'string' || !mongoUri.trim()) {
      return { ok: false, error: 'Invalid URI' };
    }
    const uri = mongoUri.trim();
    saveConfig(app, { mongoUri: uri });
    try {
      await mongoHub.connectMongo(uri);
      setConnectionError(null);
      return { ok: true };
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setConnectionError(msg);
      return { ok: false, error: msg };
    }
  });

  ipcMain.handle('auth:login', async (_e, username, password) => {
    try {
      return await withDb(async (db) => {
        const doc = await db.collection('users').findOne({ username: String(username) });
        if (!doc) return { ok: false, error: 'Invalid credentials' };
        const derived = hashPassword(String(password), String(doc.salt));
        if (derived !== doc.passwordHash) return { ok: false, error: 'Invalid credentials' };
        const user = safeUser(doc);
        setUser(user);
        return { ok: true, user };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('auth:session', async () => getUser());

  ipcMain.handle('auth:logout', async () => {
    setUser(null);
    return { ok: true };
  });

  ipcMain.handle('menu:list', async () => {
    try {
      return await withDb(async (db) => {
        const docs = await db
          .collection('menu_items')
          .find({ active: true })
          .sort({ name: 1 })
          .toArray();
        return docs.map(safeMenuItem);
      });
    } catch (e) {
      return [];
    }
  });

  ipcMain.handle('floor:list', async () => {
    try {
      return await withDb(async (db) => {
        const areas = await db.collection('areas').find().sort({ sort: 1 }).toArray();
        const tables = await db.collection('tables').find().sort({ name: 1 }).toArray();
        return areas.map((a) => ({
          id: a._id.toString(),
          name: a.name,
          tables: tables
            .filter((t) => t.areaId.toString() === a._id.toString())
            .map((t) => ({
              id: t._id.toString(),
              name: t.name,
              capacity: t.capacity,
              status: t.status,
              currentOrderId: t.currentOrderId ? t.currentOrderId.toString() : null,
            })),
        }));
      });
    } catch (e) {
      return [];
    }
  });

  ipcMain.handle('orders:startOrOpenForTable', async (_e, tableId) => {
    try {
      return await withDb(async (db) => {
        const tid = new ObjectId(String(tableId));
        const table = await db.collection('tables').findOne({ _id: tid });
        if (!table) return { ok: false, error: 'Table not found' };

        if (table.currentOrderId) {
          const existing = await db.collection('orders').findOne({ _id: table.currentOrderId });
          if (existing && existing.status !== 'closed') {
            return { ok: true, order: safeOrder(existing) };
          }
          await db.collection('tables').updateOne(
            { _id: tid },
            { $set: { status: 'free', currentOrderId: null } },
          );
        }

        const orderDoc = {
          orderType: 'dine_in',
          tableId: tid,
          status: 'open',
          lines: [],
          subtotalCents: 0,
          totalCents: 0,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        const ins = await db.collection('orders').insertOne(orderDoc);
        await db.collection('tables').updateOne(
          { _id: tid },
          { $set: { status: 'occupied', currentOrderId: ins.insertedId } },
        );
        return {
          ok: true,
          order: safeOrder({ ...orderDoc, _id: ins.insertedId }),
        };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('orders:getById', async (_e, orderId) => {
    try {
      return await withDb(async (db) => {
        const o = await db.collection('orders').findOne({ _id: new ObjectId(String(orderId)) });
        return o ? safeOrder(o) : null;
      });
    } catch {
      return null;
    }
  });

  ipcMain.handle('orders:addLines', async (_e, orderId, items) => {
    try {
      return await withDb(async (db) => {
        const oid = new ObjectId(String(orderId));
        const order = await db.collection('orders').findOne({
          _id: oid,
          status: { $in: ['open', 'kot_sent'] },
        });
        if (!order) return { ok: false, error: 'Order not found or locked' };

        const lines = [...(order.lines || [])];
        for (const it of items || []) {
          const mid = new ObjectId(String(it.menuItemId));
          const menu = await db.collection('menu_items').findOne({ _id: mid, active: true });
          if (!menu) return { ok: false, error: 'Menu item not found' };
          const qty = Math.max(1, Number(it.qty) || 1);
          if (menu.stock < qty) return { ok: false, error: `Insufficient stock: ${menu.name}` };
          lines.push({
            lineId: crypto.randomUUID(),
            menuItemId: mid,
            nameSnapshot: menu.name,
            qty,
            unitPriceCents: menu.priceCents,
            kotStatus: 'pending',
          });
        }
        const { subtotalCents, totalCents } = totalsFromLines(lines);
        await db.collection('orders').updateOne(
          { _id: oid },
          { $set: { lines, subtotalCents, totalCents, updatedAt: new Date() } },
        );
        const fresh = await db.collection('orders').findOne({ _id: oid });
        return { ok: true, order: safeOrder(fresh) };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('orders:sendKot', async (_e, orderId) => {
    try {
      return await withDb(async (db) => {
        const oid = new ObjectId(String(orderId));
        const order = await db.collection('orders').findOne({
          _id: oid,
          status: { $in: ['open', 'kot_sent'] },
        });
        if (!order) return { ok: false, error: 'Order not found' };
        const lines = (order.lines || []).map((l) =>
          l.kotStatus === 'pending' ? { ...l, kotStatus: 'sent' } : l,
        );
        const anySent = lines.some((l) => l.kotStatus === 'sent');
        await db.collection('orders').updateOne(
          { _id: oid },
          {
            $set: {
              lines,
              status: anySent ? 'kot_sent' : order.status,
              updatedAt: new Date(),
            },
          },
        );
        const fresh = await db.collection('orders').findOne({ _id: oid });
        return { ok: true, order: safeOrder(fresh) };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('kitchen:queue', async () => {
    try {
      return await withDb(async (db) => {
        const orders = await db
          .collection('orders')
          .find({
            status: { $in: ['open', 'kot_sent'] },
            lines: {
              $elemMatch: { kotStatus: { $in: ['sent', 'preparing', 'ready'] } },
            },
          })
          .sort({ updatedAt: 1 })
          .toArray();
        return orders.map(safeOrder);
      });
    } catch {
      return [];
    }
  });

  ipcMain.handle('kitchen:updateLine', async (_e, orderId, lineId, status) => {
    const allowed = ['preparing', 'ready', 'served'];
    if (!allowed.includes(String(status))) {
      return { ok: false, error: 'Invalid status' };
    }
    try {
      return await withDb(async (db) => {
        const oid = new ObjectId(String(orderId));
        const order = await db.collection('orders').findOne({ _id: oid });
        if (!order) return { ok: false, error: 'Order not found' };
        const lines = (order.lines || []).map((l) => {
          if (l.lineId !== lineId) return l;
          const cur = l.kotStatus;
          const next = String(status);
          const transitionOk =
            (cur === 'sent' && ['preparing', 'ready', 'served'].includes(next)) ||
            (cur === 'preparing' && ['ready', 'served'].includes(next)) ||
            (cur === 'ready' && next === 'served');
          return transitionOk ? { ...l, kotStatus: next } : l;
        });
        await db.collection('orders').updateOne(
          { _id: oid },
          { $set: { lines, updatedAt: new Date() } },
        );
        const fresh = await db.collection('orders').findOne({ _id: oid });
        return { ok: true, order: safeOrder(fresh) };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('orders:complete', async (_e, orderId) => {
    try {
      return await withDb(async (db) => {
        const oid = new ObjectId(String(orderId));
        const order = await db.collection('orders').findOne({
          _id: oid,
          status: { $in: ['open', 'kot_sent'] },
        });
        if (!order) return { ok: false, error: 'Order not found or already closed' };
        if (!order.lines || order.lines.length === 0) {
          return { ok: false, error: 'Order is empty' };
        }

        for (const line of order.lines) {
          const m = await db.collection('menu_items').findOne({ _id: line.menuItemId });
          if (!m) return { ok: false, error: 'Menu item missing' };
          if (m.stock < line.qty) return { ok: false, error: `Insufficient stock: ${m.name}` };
        }

        for (const line of order.lines) {
          await db.collection('menu_items').updateOne(
            { _id: line.menuItemId },
            { $inc: { stock: -line.qty } },
          );
        }

        const { subtotalCents, totalCents } = totalsFromLines(order.lines);
        await db.collection('orders').updateOne(
          { _id: oid },
          {
            $set: {
              status: 'closed',
              subtotalCents,
              totalCents,
              closedAt: new Date(),
              updatedAt: new Date(),
            },
          },
        );

        if (order.tableId) {
          await db.collection('tables').updateOne(
            { _id: order.tableId },
            { $set: { status: 'free', currentOrderId: null } },
          );
        }

        return { ok: true, orderId: oid.toString(), totalCents };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });

  ipcMain.handle('orders:createWalkIn', async (_e, items) => {
    if (!Array.isArray(items) || items.length === 0) {
      return { ok: false, error: 'Cart is empty' };
    }
    try {
      return await withDb(async (db) => {
        const lines = [];
        for (const it of items) {
          const mid = new ObjectId(String(it.menuItemId));
          const menu = await db.collection('menu_items').findOne({ _id: mid, active: true });
          if (!menu) return { ok: false, error: 'Menu item not found' };
          const qty = Math.max(1, Number(it.qty) || 1);
          if (menu.stock < qty) return { ok: false, error: `Insufficient stock: ${menu.name}` };
          lines.push({
            lineId: crypto.randomUUID(),
            menuItemId: mid,
            nameSnapshot: menu.name,
            qty,
            unitPriceCents: menu.priceCents,
            kotStatus: 'served',
          });
        }

        for (const line of lines) {
          await db.collection('menu_items').updateOne(
            { _id: line.menuItemId },
            { $inc: { stock: -line.qty } },
          );
        }

        const { subtotalCents, totalCents } = totalsFromLines(lines);
        const doc = {
          orderType: 'takeaway',
          tableId: null,
          status: 'closed',
          lines,
          subtotalCents,
          totalCents,
          createdAt: new Date(),
          updatedAt: new Date(),
          closedAt: new Date(),
        };
        const ins = await db.collection('orders').insertOne(doc);
        return { ok: true, orderId: ins.insertedId.toString(), totalCents };
      });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  });
}

module.exports = { registerIpc };
