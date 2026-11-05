import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Mindcatch mobile shell (Capacitor 6).
 *
 * НЕ bundled UI: застосунок — тонка оболонка, яка підключається до СВОГО
 * сервера (self-hosted етос проєкту). Адреса сервера вводиться на splash
 * screen при першому запуску (www/shell.js) і зберігається в Preferences —
 * тому `server.url` тут НЕ задається статично.
 */
const config: CapacitorConfig = {
  appId: 'io.github.xydik1otto.mindcatch',
  appName: 'Mindcatch',
  webDir: 'www',
};

export default config;
