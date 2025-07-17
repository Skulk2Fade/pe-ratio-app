const CACHE_NAME = 'pe-ratio-cache-v3';
const urlsToCache = [
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/vendor/bootstrap.min.css',
  '/static/vendor/bootstrap.bundle.min.js',
  '/static/vendor/plotly.min.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Remove old caches on activate so outdated HTML is not served
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      )
    )
  );
});

async function updateData() {
  try {
    const resp = await fetch('/api/watchlist', { credentials: 'include' });
    if (resp.ok) {
      const cache = await caches.open('data-cache');
      await cache.put('/api/watchlist', resp.clone());
    }
  } catch (e) {
    console.error('Background data refresh failed', e);
  }
}

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

self.addEventListener('push', event => {
  let data = {};
  if (event.data) {
    try { data = event.data.json(); } catch (e) { data = {body: event.data.text()}; }
  }
  const title = data.title || 'MarketMinder Alert';
  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    actions: data.actions || [
      { action: 'view', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    data: { url: data.url || '/alerts' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') {
    return;
  }
  if (event.action === 'refresh') {
    event.waitUntil(updateData());
  } else {
    const url = event.notification.data && event.notification.data.url;
    event.waitUntil(clients.openWindow(url || '/'));
  }
});

self.addEventListener('sync', event => {
  if (event.tag === 'refresh-data') {
    event.waitUntil(updateData());
  }
});
