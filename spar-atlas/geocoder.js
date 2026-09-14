/* Geoapify city lookup. No names, emails or project details are sent. */
(function(root){
  'use strict';
  function create(options){
    options = options || {};
    var apiKey = options.apiKey || '';
    var endpoint = options.endpoint || 'https://api.geoapify.com/v1/geocode/search';
    var fetcher = options.fetch || root.fetch.bind(root);
    var storage = options.storage;
    if(storage === undefined){ try { storage = root.localStorage; } catch(e){} }
    var cache = new Map(), pending = new Map(), queue = Promise.resolve();
    var cacheKey = 'spar-atlas-geoapify-v1', ttl = 30 * 86400000, cooldown = 0;
    var interval = options.interval === undefined ? 350 : options.interval;
    function key(text){ return String(text || '').trim().toLowerCase().replace(/\s+/g, ' '); }
    function valid(p){
      return p && typeof p.label === 'string' && p.label.length > 0 &&
        Number.isFinite(p.lat) && Math.abs(p.lat) <= 90 &&
        Number.isFinite(p.lon) && Math.abs(p.lon) <= 180;
    }
    try {
      var saved = JSON.parse(storage.getItem(cacheKey) || '[]');
      saved.slice(-500).forEach(function(item){
        if(Array.isArray(item) && typeof item[0] === 'string' && item[1] &&
          item[1].expires > Date.now() && Array.isArray(item[1].results) && item[1].results.every(valid))
          cache.set(item[0], item[1]);
      });
    } catch(e){}
    function remember(k, results){
      cache.delete(k);
      cache.set(k, { expires:Date.now() + ttl, results:results });
      while(cache.size > 500) cache.delete(cache.keys().next().value);
      try { storage.setItem(cacheKey, JSON.stringify(Array.from(cache))); } catch(e){}
    }
    function lookup(text){
      text = String(text || '').trim();
      var k = key(text), hit = cache.get(k);
      if(!apiKey || !k) return Promise.resolve([]);
      if(hit && hit.expires > Date.now()) return Promise.resolve(hit.results);
      if(pending.has(k)) return pending.get(k);
      var work = queue.then(async function(){
        if(Date.now() < cooldown) throw new Error('Location service temporarily unavailable');
        var url = new URL(endpoint, root.location ? root.location.href : undefined);
        url.search = new URLSearchParams({ text:text, type:'city', format:'json', limit:'5',
          lang:'en', bias:'countrycode:none', apiKey:apiKey }).toString();
        var controller = new AbortController();
        var timer = setTimeout(function(){ controller.abort(); }, options.timeout || 8000);
        try {
          var response = await fetcher(url.href, { signal:controller.signal, credentials:'omit' });
          if(!response.ok) throw new Error('Location service unavailable (' + response.status + ')');
          var body = await response.json();
          if(!body || !Array.isArray(body.results)) throw new Error('Invalid location response');
          var results = body.results.map(function(p){
            if(p.result_type !== 'city') return null;
            var label = [p.city || p.name, p.state, p.country].filter(Boolean).join(', ');
            return { lat:p.lat, lon:p.lon, label:label,
              confidence:p.rank && p.rank.confidence, source:'geoapify' };
          }).filter(valid);
          remember(k, results);
          return results;
        } catch(error){
          // Do not persist failures or retry every roster entry after a quota/auth error.
          cooldown = Date.now() + 60000;
          throw error;
        } finally { clearTimeout(timer); }
      });
      pending.set(k, work);
      queue = work.catch(function(){}).then(function(){
        return new Promise(function(resolve){ setTimeout(resolve, interval); });
      });
      work.then(function(){ pending.delete(k); }, function(){ pending.delete(k); });
      return work;
    }
    function best(results){
      if(!results.length || !(results[0].confidence >= 0.8)) return null;
      if(results[1] && results[1].confidence >= results[0].confidence &&
         results[1].label !== results[0].label) return null;
      return results[0];
    }
    return { enabled:!!apiKey, lookup:lookup, best:best };
  }
  root.AtlasGeocoder = { create:create };
  if(typeof module !== 'undefined') module.exports = root.AtlasGeocoder;
})(typeof window !== 'undefined' ? window : globalThis);
