const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { loadConfig } = require('./configStore.cjs');
const mongoHub = require('./mongoHub.cjs');
const { registerIpc } = require('./ipcRegister.cjs');

let currentUser = null;
let bootstrapped = false;
let connectionError = null;

function setConnectionError(msg) {
  connectionError = msg;
}

function getConnectionError() {
  return connectionError;
}

async function bootstrap() {
  if (bootstrapped) return;
  const cfg = loadConfig(app);
  try {
    await mongoHub.connectMongo(cfg.mongoUri);
    connectionError = null;
  } catch (e) {
    connectionError = e instanceof Error ? e.message : String(e);
  }

  registerIpc(ipcMain, {
    app,
    mongoHub,
    getConnectionError,
    setConnectionError,
    getUser: () => currentUser,
    setUser: (u) => {
      currentUser = u;
    },
  });

  bootstrapped = true;
}

async function createWindow() {
  await bootstrap();

  const win = new BrowserWindow({
    width: 1320,
    height: 840,
    minWidth: 1024,
    minHeight: 640,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.once('ready-to-show', () => win.show());

  const dev = process.env.ELECTRON_DEV === '1';
  if (dev) {
    await win.loadURL('http://localhost:5173');
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    await win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', async () => {
  await mongoHub.disconnectMongo();
});
