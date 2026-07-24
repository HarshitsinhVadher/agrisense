const CACHE_NAME = 'agrisense-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/styles.css',
  '/static/js/translations.js',
  '/static/js/weather_ui.js',
  '/static/js/recommendation_ui.js',
  '/static/js/soil_card_ui.js',
  '/static/js/label_scanner_ui.js',
  '/static/js/profile_ui.js',
  '/static/js/app.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
