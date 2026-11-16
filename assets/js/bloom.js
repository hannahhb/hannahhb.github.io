// ASCII bloom: an endless zoom into a lily petal, drawn in its own source code.
// Every flower carries buds on three petals. The camera falls toward one bud,
// which opens into a full flower carrying buds of its own, and so on.
(function bloom() {
  var pre = document.getElementById('bloom');
  if (!pre) return;

  var SRC = bloom.toString().replace(/\s+/g, '');
  var TAU = Math.PI * 2;
  var N = 6;                       // petals per flower
  var S = 0.13;                    // bud scale relative to its parent
  var PHI = 0.55;                  // rotation per level while zooming
  var BETA = Math.PI / 2;          // a closed bud points up
  var BUD_U = 0.6;                 // how far along the petal buds sit
  var BUD_PETALS = [0, 2, 4];
  var PALETTE = [
    [232, 113, 90],   // coral
    [180, 138, 214],  // lilac
    [232, 211, 106],  // butter
    [229, 143, 180],  // pink
    [226, 222, 214]   // pale
  ];
  var GREEN = [122, 168, 110];
  var WHITE = [245, 240, 230];

  function rot(x, y, a) {
    var c = Math.cos(a), s = Math.sin(a);
    return [x * c - y * s, x * s + y * c];
  }
  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function smooth(x) { x = clamp01(x); return x * x * (3 - 2 * x); }
  function hash(a, b) {
    var h = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
    return h - Math.floor(h);
  }

  // Buds: position on the parent and their rotation. Bud 0 is the zoom path.
  var BUDS = BUD_PETALS.map(function (k, i) {
    var a = BETA + k * TAU / N;
    return { x: BUD_U * Math.cos(a), y: BUD_U * Math.sin(a), r: PHI + i * 2.1 };
  });
  // Fixed point of p -> bud0 + S * R(PHI) * p, which the camera falls toward.
  var FP = (function () {
    var x = 0, y = 0;
    for (var i = 0; i < 60; i++) {
      var q = rot(x, y, PHI);
      x = BUDS[0].x + S * q[0];
      y = BUDS[0].y + S * q[1];
    }
    return [x, y];
  })();

  function petalAngle(k, o) {
    return BETA + o * (k * TAU / N + 0.12 * Math.sin(k * 1.7));
  }

  // Shade one flower at local point (x, y) with openness o.
  // Returns {i: intensity, c: rgb, ch: optional char} or null.
  // m is the time in seconds; when given, petals sway and breathe a little.
  function flower(x, y, o, col, m) {
    var r = Math.sqrt(x * x + y * y);
    if (r > 1.1) return null;
    var L0 = 0.32 + 0.68 * o;
    var wmax = 0.17 + 0.15 * o;
    var best = null, bestE = 0, bestU = 0, bestV = 0;
    for (var k = 0; k < N; k++) {
      var a = petalAngle(k, o), L = L0;
      if (m != null) {
        a += 0.07 * Math.sin(m * 0.9 + k * 1.3);
        L *= 1 + 0.045 * Math.sin(m * 1.3 + k * 2.1);
      }
      var p = rot(x, y, -a);
      var u = p[0] / L, v = p[1] / L;
      if (u <= 0 || u >= 1) continue;
      v -= 0.07 * Math.sin(k * 2.3) * u * u * o;   // lily petals curl
      var w = wmax * 2.3 * Math.pow(u, 0.55) * Math.pow(1 - u, 0.85);
      var e = 1 - Math.abs(v) / w;
      if (e > bestE) { bestE = e; bestU = u; bestV = v; best = k; }
    }
    // stamens between petals, white star at the centre
    if (o > 0.4) {
      for (var j = 0; j < N; j++) {
        var sa = petalAngle(j, o) + Math.PI / N + (m != null ? 0.05 * Math.sin(m * 1.1 + j) : 0);
        var sp = rot(x, y, -sa);
        var len = 0.38 * o;
        if (sp[0] > 0 && sp[0] < len && Math.abs(sp[1]) < 0.012 + 0.01 * (1 - sp[0] / len)) {
          return { i: 0.8, c: WHITE, ch: '|' };
        }
        var dx = sp[0] - len, dy = sp[1];
        if (dx * dx + dy * dy < 0.0007) return { i: 1, c: PALETTE[2], ch: '*' };
      }
    }
    if (r < 0.07 + 0.05 * o) return { i: 1, c: WHITE };
    if (best === null) {
      // closed buds sit on a green calyx
      if (o < 0.7 && y < 0 && y > -0.18 && Math.abs(x) < 0.08 * (1 + y / 0.18) + 0.02) {
        return { i: 0.7, c: GREEN };
      }
      return null;
    }
    var vein = Math.abs(bestV) < 0.018 ? 0.35 : 0;
    var side = 0.12 * Math.max(0, Math.cos(38 * (bestU - 1.6 * Math.abs(bestV))));
    var inten = 0.45 + 0.4 * bestE + vein + side;
    var base = PALETTE[col % PALETTE.length];
    var t = smooth((0.3 - bestU) / 0.3) * 0.7 * o;   // pale throat like a lily
    var c = [base[0] + (255 - base[0]) * t, base[1] + (255 - base[1]) * t, base[2] + (255 - base[2]) * t];
    return { i: Math.min(1, inten), c: c, ch: bestE < 0.14 ? (bestU > 0.9 ? '.' : ':') : null };
  }

  // Evaluate the level-d flower and its buds at local point (x, y).
  function level(x, y, d, ctx) {
    var o = ctx.open(d);
    if (d < ctx.maxD && o > 0.97) {
      var g = smooth((o - 0.97) / 0.03);
      for (var b = 0; b < BUDS.length; b++) {
        var B = BUDS[b];
        var q = rot(x - B.x, y - B.y, -B.r);
        var qx = q[0] / (S * g), qy = q[1] / (S * g);
        if (qx * qx + qy * qy < 1.1) {
          var hit = level(qx, qy, d + 1, ctx);
          if (hit) return hit;
        }
      }
    }
    var h = flower(x, y, o, ctx.col + d, d === 0 ? ctx.m : null);   // buds stay still
    if (h) { var f = ctx.fade(d); h.i *= f; h.thin = 1 - f; }
    return h;
  }

  // Root scene: a small bouquet with stems. The root flower is index 0.
  var SIBS = [
    { x: -1.5, y: -1.0, s: 0.72, r: 0.45, col: 1 },
    { x: 1.45, y: -0.65, s: 0.68, r: -0.55, col: 2 }
  ];
  var STEMS = [[0, 0], [-1.5, -1.0], [1.45, -0.65]];
  // flower centres and radii in world units, for hit testing and labels
  var FLOWERS = [{ x: 0, y: 0, s: 1, r: 0 }].concat(SIBS);
  function flowerAt(x, y) {
    for (var i = 0; i < FLOWERS.length; i++) {
      var F = FLOWERS[i];
      if (Math.hypot(x - F.x, y - F.y) < F.s * 1.02) return i;
    }
    return -1;
  }
  function rootExtras(x, y, o, m) {
    for (var i = 0; i < SIBS.length; i++) {
      var F = SIBS[i];
      var q = rot(x - F.x, y - F.y, -F.r);
      var h = flower(q[0] / F.s, q[1] / F.s, o, F.col, m == null ? null : m + 2.3 * (i + 1));
      if (h) return h;
    }
    // stems converge to a point below the bouquet
    var gx = 0.1, gy = -4.3;
    for (var j = 0; j < STEMS.length; j++) {
      var sx = STEMS[j][0], sy = STEMS[j][1];
      var vx = gx - sx, vy = gy - sy, l2 = vx * vx + vy * vy;
      var t = ((x - sx) * vx + (y - sy) * vy) / l2;
      if (t < 0.05 || t > 1) continue;
      var px = sx + vx * t, py = sy + vy * t;
      var dd = Math.hypot(x - px, y - py);
      if (dd < 0.045) return { i: 0.75, c: GREEN, ch: '|' };
      // a leaf partway down each stem
      var lt = (t - 0.55) / 0.35;
      if (lt > 0 && lt < 1 && dd < 0.2 * Math.sin(Math.PI * lt) && (x - px) * (j % 2 ? 1 : -1) > 0) {
        return { i: 0.45 + 0.3 * (1 - dd / 0.2), c: GREEN };
      }
    }
    return null;
  }

  var cols = 0, rows = 0, cw = 6, lh = 11, padL = 0, padT = 0;
  function measure() {
    var probe = document.createElement('span');
    probe.textContent = 'MMMMMMMMMM';
    pre.appendChild(probe);
    cw = probe.getBoundingClientRect().width / 10;
    pre.removeChild(probe);
    var cs = getComputedStyle(pre);
    lh = parseFloat(cs.lineHeight) || cw * 1.8;
    padL = parseFloat(cs.paddingLeft); padT = parseFloat(cs.paddingTop);
    var padX = padL + parseFloat(cs.paddingRight);
    var padY = padT + parseFloat(cs.paddingBottom);
    cols = Math.max(20, Math.floor((pre.clientWidth - padX - 1) / cw));
    rows = Math.max(16, Math.floor((pre.clientHeight - padY - 1) / lh));
  }

  function esc(ch) {
    return ch === '<' ? '&lt;' : ch === '>' ? '&gt;' : ch === '&' ? '&amp;' : ch;
  }

  var HALF = 1.25;
  var REST_T = -0.03;                       // the bouquet, fully open
  var REST = { x: 0, y: -0.6, scale: 1 };
  // fit the bouquet (flowers plus the top of the stems) to the panel
  function fitRest() {
    var U = unit();
    var halfW = cols * cw / 2 / U, halfH = rows * lh / 2 / U;
    REST.scale = Math.max(2.4 / halfW, 2.0 / halfH);
    REST.y = 1.35 - halfH * REST.scale;     // top flower near the top, stems run down
  }
  function unit() { return Math.min(cols * cw, rows * lh) / 2 / HALF; }   // px per screen unit

  // Draw one frame. t sets how open each level is; cam says where the camera looks
  // (null means the endless petal zoom). hover dims every flower but that one.
  // Grass along the bottom of the panel, in screen cells. Each blade bends with the wind.
  function grass(c, rb, m) {
    var best = null;
    for (var j = c - 3; j <= c + 3; j++) {
      var hj = hash(j, 7.3);
      if (hj < 0.3) continue;
      var H = 2 + Math.floor(hash(j, 2.9) * Math.min(9, rows * 0.12));
      if (rb >= H) continue;
      var wind = Math.sin(m * 1.4 - j * 0.18) + 0.35 * Math.sin(m * 3.1 + j * 0.9);
      var lean = (0.8 + hj) * wind;
      var y = (rb + 0.5) / H;
      var x = j + lean * y * y;
      if (Math.abs(x - c) > 0.5) continue;
      var slope = 2 * lean * y / H;
      var ch = rb === H - 1 ? (slope > 0.25 ? '/' : slope < -0.25 ? '\\' : "'") :
               slope > 0.3 ? '/' : slope < -0.3 ? '\\' : '|';
      var g = 0.45 + 0.4 * hash(j, 5.1) + 0.15 * y;
      best = { i: Math.min(1, g), c: hj > 0.85 ? [150, 190, 110] : GREEN, ch: ch };
      if (j === c) break;
    }
    return best;
  }

  function frame(t, tick, cam, hover, m) {
    var n = Math.floor(t);
    var off = Math.max(0, n - 2);      // renormalise so floats never underflow
    var tl = t - off;
    var ctx = {
      m: m,
      maxD: Math.floor(tl) + 3,
      col: off,
      open: function (d) { return smooth(tl - d + 1); },
      // a flower fades into background texture once its bud takes over the frame
      fade: function (d) { return 0.28 + 0.72 * smooth(1 - (tl - d - 0.15) / 0.75); }
    };
    var scale = Math.pow(S, tl), ang = PHI * Math.max(tl, 0);
    var U = unit();
    var out = [], last = '', run = '';
    var shift = Math.floor(tick / 5);
    for (var row = 0; row < rows; row++) {
      for (var c = 0; c < cols; c++) {
        var qx = (c - cols / 2 + 0.5) * cw / U;
        var qy = (rows / 2 - row - 0.5) * lh / U;
        var wx, wy;
        if (cam) {
          wx = cam.x + qx * cam.scale; wy = cam.y + qy * cam.scale;
        } else {
          var d = rot(qx - FP[0], qy - FP[1], ang);
          wx = FP[0] + scale * d[0]; wy = FP[1] + scale * d[1];
        }
        var hit = m != null && !(cam && cam.fly) ? grass(c, rows - 1 - row, m) : null;
        if (!hit) hit = level(wx, wy, 0, ctx);
        if (!hit && off === 0 && tl < 1.2) hit = rootExtras(wx, wy, ctx.open(0), m);
        if (hit && hover != null && hover >= 0 && flowerAt(wx, wy) !== hover) {
          hit = { i: hit.i * 0.45, c: hit.c, ch: hit.ch, thin: hit.thin };
        }
        var ch, color;
        if (hit && hit.thin && hash(c * 1.37 + 3, row * 0.71) < hit.thin * 0.65 && !hit.ch) hit = null;
        if (hit) {
          var q = Math.round(hit.i * 5) / 5;
          var k = 0.2 + 0.8 * q;
          color = 'rgb(' + (hit.c[0] * k | 0) + ',' + (hit.c[1] * k | 0) + ',' + (hit.c[2] * k | 0) + ')';
          if (hit.ch) ch = hit.ch;
          else if (hit.thin > 0.35) ch = hit.i > 0.32 ? ':' : '.';   // faded petals become dotted ground
          else ch = SRC.charAt((row * cols + c + shift) % SRC.length);
        } else {
          var hs = hash(c, row);
          if (hs > 0.985) {
            var tw = 0.4 + 0.6 * Math.abs(Math.sin(tick * 0.05 + hs * 50));
            var v = (90 + 150 * tw) | 0;
            color = 'rgb(' + v + ',' + v + ',' + v + ')';
            ch = hs > 0.996 ? '*' : '.';
          } else { color = ''; ch = ' '; }
        }
        if (color !== last) {
          if (run) out.push(last ? '<span style="color:' + last + '">' + run + '</span>' : run);
          run = ''; last = color;
        }
        run += esc(ch);
      }
      run += '\n';
    }
    if (run) out.push(last ? '<span style="color:' + last + '">' + run + '</span>' : run);
    pre.innerHTML = out.join('');
  }

  // Screen <-> world for the resting bouquet, in px relative to the <pre>.
  function toWorld(px, py) {
    var U = unit();
    var qx = (px - padL - cols * cw / 2) / U, qy = (rows * lh / 2 - (py - padT)) / U;
    return [REST.x + qx * REST.scale, REST.y + qy * REST.scale];
  }
  function toScreen(wx, wy) {
    var U = unit();
    return [padL + cols * cw / 2 + (wx - REST.x) / REST.scale * U,
            padT + rows * lh / 2 - (wy - REST.y) / REST.scale * U];
  }

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hover = -1, busy = false, t0 = performance.now(), tick = 0;
  function now() { return reduce ? null : (performance.now() - t0) / 1000; }
  function still() { frame(REST_T, tick, REST, hover, now()); }
  measure(); fitRest();
  still();
  // gentle idle loop: petals sway, grass blows; buds and layout stay put
  var lastDraw = 0;
  function idle(ts) {
    requestAnimationFrame(idle);
    if (busy || document.hidden || ts - lastDraw < 66) return;   // ~15 fps is plenty
    lastDraw = ts; tick++;
    still();
  }
  if (!reduce) requestAnimationFrame(idle);
  window.addEventListener('resize', function () {
    measure(); fitRest();
    if (!busy) still();
    if (api.onlayout) api.onlayout();
  });

  // Fly into flower i (into its petal, where a bud sits on the centre flower), then call done.
  function flyInto(i, done) {
    var F = FLOWERS[i];
    var tip = rot(0, BUD_U * F.s, F.r);
    var to = { x: F.x + tip[0], y: F.y + tip[1], scale: REST.scale * F.s * 0.05 };
    if (reduce) { done(); return; }
    busy = true;
    var start = null, DUR = 1400;
    function step(now) {
      if (start === null) start = now;
      var p = Math.min(1, (now - start) / DUR);
      var e = p * p * (3 - 2 * p);
      var ls = Math.log(REST.scale) + (Math.log(to.scale) - Math.log(REST.scale)) * e;  // zoom evenly in log space
      var cam = { x: REST.x + (to.x - REST.x) * e, y: REST.y + (to.y - REST.y) * e, scale: Math.exp(ls), fly: true };
      frame(REST_T, tick++, cam, i, now());
      if (p < 1) requestAnimationFrame(step);
      else { busy = false; done(); }
    }
    requestAnimationFrame(step);
  }

  var api = window.Bloom = {
    flowers: function () {
      return FLOWERS.map(function (F) {
        var c = toScreen(F.x, F.y), top = toScreen(F.x, F.y + F.s);
        return { x: c[0], y: c[1], top: top[1], r: c[1] - top[1] };
      });
    },
    flowerAtPoint: function (px, py) { var w = toWorld(px, py); return flowerAt(w[0], w[1]); },
    hover: function (i) { if (busy || i === hover) return; hover = i; still(); },
    flyInto: flyInto,
    reset: function () { busy = false; hover = -1; still(); },
    onlayout: null
  };
})();
