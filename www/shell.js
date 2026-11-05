/**
 * Mindcatch mobile shell — splash screen з полем «Адреса сервера».
 *
 * Застосунок не містить bundled UI: перший запуск → користувач вводить адресу
 * свого сервера → перевірка → редірект на сервер (повний PWA UI). Адреса
 * зберігається в @capacitor/preferences (нативні Preferences), з fallback
 * на localStorage у веб-контексті.
 */
(function () {
  'use strict';

  var KEY = 'mindcatch_server_url';

  // UA/EN i18n (авто-детект мови системи)
  var ua = (navigator.language || '').toLowerCase().indexOf('uk') === 0;
  var T = ua
    ? {
        sub: 'Підключіться до свого сервера — усе зберігається у вас.',
        placeholder: 'http://192.168.1.10:8000',
        go: 'Підключитися',
        checking: 'Перевіряю…',
        ok: 'Сервер знайдено! Відкриваю…',
        errNet: 'Не вдалося підключитися. Перевірте адресу і мережу.',
        errNotServer: 'Це не схоже на Mindcatch-сервер (немає /api/tags).',
        saved: 'Збережений сервер не відповідає — введіть адресу знову.',
        hint: 'Сервер запускається командою <code>mindcatch</code> або <code>python -m app.main</code>. Для віддаленого доступу використовуйте Tailscale/WireGuard (див. MOBILE.md).'
      }
    : {
        sub: 'Connect to your own server — everything stays with you.',
        placeholder: 'http://192.168.1.10:8000',
        go: 'Connect',
        checking: 'Checking…',
        ok: 'Server found! Opening…',
        errNet: 'Could not connect. Check the address and network.',
        errNotServer: 'That does not look like a Mindcatch server (no /api/tags).',
        saved: 'Saved server is unreachable — enter the address again.',
        hint: 'Start the server with <code>mindcatch</code> or <code>python -m app.main</code>. For remote access use Tailscale/WireGuard (see MOBILE.md).'
      };

  var $ = function (id) { return document.getElementById(id); };

  function t(key) { return T[key]; }

  function setMsg(text, cls) {
    var el = $('msg');
    el.textContent = text || '';
    el.className = 'msg' + (cls ? ' ' + cls : '');
  }

  function normalize(url) {
    url = (url || '').trim().replace(/\/+$/, '');
    if (!url) return '';
    if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
    return url;
  }

  // Preferences: нативний плагін через window.Capacitor.Plugins (runtime
  // реєструє всі встановлені плагіни), fallback — localStorage.
  function prefsGet(key) {
    var Cap = window.Capacitor;
    if (Cap && Cap.isNativePlatform && Cap.isNativePlatform() && Cap.Plugins && Cap.Plugins.Preferences) {
      return Cap.Plugins.Preferences.get({ key: key }).then(function (r) { return r.value || ''; });
    }
    return Promise.resolve(localStorage.getItem(key) || '');
  }

  function prefsSet(key, value) {
    var Cap = window.Capacitor;
    if (Cap && Cap.isNativePlatform && Cap.isNativePlatform() && Cap.Plugins && Cap.Plugins.Preferences) {
      return Cap.Plugins.Preferences.set({ key: key, value: value });
    }
    localStorage.setItem(key, value);
    return Promise.resolve();
  }

  function probe(url) {
    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = ctrl && setTimeout(function () { ctrl.abort(); }, 6000);
    return fetch(url + '/api/tags', {
      method: 'GET',
      signal: ctrl ? ctrl.signal : undefined,
      headers: { 'Accept': 'application/json' }
    }).then(function (res) {
      if (timer) clearTimeout(timer);
      return res.ok;
    }).catch(function () {
      if (timer) clearTimeout(timer);
      return false;
    });
  }

  function connect(url, isSaved) {
    if (!url) { setMsg(t('errNet'), 'err'); return; }
    $('go').disabled = true;
    setMsg(t('checking'));
    probe(url).then(function (alive) {
      $('go').disabled = false;
      if (!alive) {
        setMsg((isSaved ? t('saved') + ' ' : '') + t('errNet'), 'err');
        return;
      }
      setMsg(t('ok'), 'ok');
      prefsSet(KEY, url).then(function () {
        // Редірект на сервер — далі весь UI віддає сервер (PWA).
        window.location.href = url + '/';
      });
    });
  }

  // Init
  document.getElementById('sub').textContent = t('sub');
  document.getElementById('go').textContent = t('go');
  document.getElementById('hint').innerHTML = t('hint');
  var input = $('server');
  input.placeholder = t('placeholder');

  prefsGet(KEY).then(function (saved) {
    if (saved) {
      input.value = saved;
      connect(saved, true); // авто-підключення до збереженого сервера
    }
    input.focus();
  });

  $('go').addEventListener('click', function () { connect(normalize(input.value), false); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') connect(normalize(input.value), false);
  });
})();
