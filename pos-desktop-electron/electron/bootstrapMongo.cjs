const { hashPassword, newSalt } = require('./cryptoUtil.cjs');

async function ensureIndexes(db) {
  await db.collection('users').createIndex({ username: 1 }, { unique: true });
  await db.collection('menu_items').createIndex({ active: 1, name: 1 });
  await db.collection('tables').createIndex({ areaId: 1, name: 1 });
  await db.collection('orders').createIndex({ tableId: 1, status: 1 });
  await db.collection('orders').createIndex({ status: 1, updatedAt: -1 });
  await db.collection('app_meta').createIndex({ key: 1 }, { unique: true });
}

async function seedIfEmpty(db) {
  const meta = await db.collection('app_meta').findOne({ key: 'schema_version' });
  if (!meta) {
    await db.collection('app_meta').insertOne({ key: 'schema_version', value: 1 });
  }

  const userCount = await db.collection('users').countDocuments();
  if (userCount > 0) return;

  const salt = newSalt();
  await db.collection('users').insertOne({
    username: 'admin',
    salt,
    passwordHash: hashPassword('admin123', salt),
    role: 'admin',
    createdAt: new Date(),
  });

  const { insertedId: areaId } = await db.collection('areas').insertOne({
    name: 'Main Hall',
    sort: 0,
  });

  await db.collection('tables').insertMany(
    Array.from({ length: 8 }, (_, i) => ({
      areaId,
      name: `T${i + 1}`,
      capacity: 4,
      status: 'free',
      currentOrderId: null,
    })),
  );

  await db.collection('menu_items').insertMany([
    {
      name: 'Tea',
      sku: 'SKU-TEA',
      priceCents: 5000,
      stock: 100,
      active: true,
      kitchenSection: 'Beverage',
    },
    {
      name: 'Paratha',
      sku: 'SKU-PAR',
      priceCents: 8000,
      stock: 50,
      active: true,
      kitchenSection: 'Kitchen',
    },
    {
      name: 'Karahi Half',
      sku: 'SKU-KAR-H',
      priceCents: 90000,
      stock: 20,
      active: true,
      kitchenSection: 'Kitchen',
    },
    {
      name: 'Karahi Full',
      sku: 'SKU-KAR-F',
      priceCents: 170000,
      stock: 15,
      active: true,
      kitchenSection: 'Kitchen',
    },
  ]);
}

module.exports = { ensureIndexes, seedIfEmpty };
