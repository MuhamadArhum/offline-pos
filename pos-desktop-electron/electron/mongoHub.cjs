const { MongoClient } = require('mongodb');
const { databaseNameFromUri } = require('./configStore.cjs');
const { ensureIndexes, seedIfEmpty } = require('./bootstrapMongo.cjs');

let client = null;
let db = null;

async function connectMongo(uri) {
  await disconnectMongo();
  client = new MongoClient(uri, { serverSelectionTimeoutMS: 8000 });
  await client.connect();
  const dbName = databaseNameFromUri(uri);
  db = client.db(dbName);
  await db.command({ ping: 1 });
  await ensureIndexes(db);
  await seedIfEmpty(db);
  return db;
}

async function disconnectMongo() {
  if (client) {
    await client.close().catch(() => {});
    client = null;
    db = null;
  }
}

function getDb() {
  if (!db) throw new Error('MongoDB not connected');
  return db;
}

function isConnected() {
  return !!db;
}

module.exports = { connectMongo, disconnectMongo, getDb, isConnected };
