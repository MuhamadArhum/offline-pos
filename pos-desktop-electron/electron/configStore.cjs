const fs = require('fs');
const path = require('path');

const DEFAULT_URI = 'mongodb://127.0.0.1:27017/offline_pos';

function configPath(app) {
  return path.join(app.getPath('userData'), 'pos-config.json');
}

function loadConfig(app) {
  const fromEnv = process.env.MONGODB_URI;
  try {
    const p = configPath(app);
    if (!fs.existsSync(p)) {
      return { mongoUri: fromEnv || DEFAULT_URI };
    }
    const j = JSON.parse(fs.readFileSync(p, 'utf8'));
    return { mongoUri: fromEnv || j.mongoUri || DEFAULT_URI };
  } catch {
    return { mongoUri: fromEnv || DEFAULT_URI };
  }
}

function saveConfig(app, cfg) {
  fs.mkdirSync(path.dirname(configPath(app)), { recursive: true });
  fs.writeFileSync(configPath(app), JSON.stringify(cfg, null, 2), 'utf8');
}

function databaseNameFromUri(uri) {
  try {
    const idx = uri.indexOf('://');
    const rest = idx >= 0 ? uri.slice(idx + 3) : uri;
    const slash = rest.indexOf('/');
    if (slash === -1 || slash === rest.length - 1) return 'offline_pos';
    const pathPart = rest.slice(slash + 1).split('?')[0];
    return pathPart || 'offline_pos';
  } catch {
    return 'offline_pos';
  }
}

module.exports = { loadConfig, saveConfig, DEFAULT_URI, databaseNameFromUri };
