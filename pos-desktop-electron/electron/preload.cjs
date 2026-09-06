const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('posApi', {
  health: () => ipcRenderer.invoke('system:health'),
  getConfig: () => ipcRenderer.invoke('config:get'),
  setMongoUri: (mongoUri) => ipcRenderer.invoke('config:setMongoUri', mongoUri),

  login: (username, password) => ipcRenderer.invoke('auth:login', username, password),
  session: () => ipcRenderer.invoke('auth:session'),
  logout: () => ipcRenderer.invoke('auth:logout'),

  listMenu: () => ipcRenderer.invoke('menu:list'),
  listFloor: () => ipcRenderer.invoke('floor:list'),

  startOrOpenForTable: (tableId) => ipcRenderer.invoke('orders:startOrOpenForTable', tableId),
  getOrder: (orderId) => ipcRenderer.invoke('orders:getById', orderId),
  addOrderLines: (orderId, items) => ipcRenderer.invoke('orders:addLines', orderId, items),
  sendKot: (orderId) => ipcRenderer.invoke('orders:sendKot', orderId),
  completeOrder: (orderId) => ipcRenderer.invoke('orders:complete', orderId),
  createWalkIn: (items) => ipcRenderer.invoke('orders:createWalkIn', items),

  kitchenQueue: () => ipcRenderer.invoke('kitchen:queue'),
  kitchenUpdateLine: (orderId, lineId, status) =>
    ipcRenderer.invoke('kitchen:updateLine', orderId, lineId, status),
});
