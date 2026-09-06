const crypto = require('crypto');

function hashPassword(password, saltHex) {
  const salt = Buffer.from(saltHex, 'hex');
  return crypto.pbkdf2Sync(password, salt, 120000, 32, 'sha256').toString('hex');
}

function newSalt() {
  return crypto.randomBytes(16).toString('hex');
}

module.exports = { hashPassword, newSalt };
