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
  function flower(x, y, o, col) {
    var r = Math.sqrt(x * x + y * y);
    if (r > 1.05) return null;
    var L = 0.32 + 0.68 * o;
    var wmax = 0.17 + 0.15 * o;
    var best = null, bestE = 0, bestU = 0, bestV = 0;
    for (var k = 0; k < N; k++) {
      var a = petalAngle(k, o);
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
        var sa = petalAngle(j, o) + Math.PI / N;
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
    var h = flower(x, y, o, ctx.col + d);
    if (h) { var f = ctx.fade(d); h.i *= f; h.thin = 1 - f; }
    return h;
  }

  // Root scene: a small bouquet with stems, only seen during the intro.
  var SIBS = [
    { x: -1.75, y: -0.9, s: 0.75, r: 0.5, col: 1 },
    { x: 1.65, y: -0.55, s: 0.7, r: -0.6, col: 2 },
    { x: 0.35, y: -2.0, s: 0.62, r: 0.2, col: 4 }
  ];
  var STEMS = [[0, 0], [-1.75, -0.9], [1.65, -0.55], [0.35, -2.0]];
  function rootExtras(x, y, o) {
    for (var i = 0; i < SIBS.length; i++) {
      var F = SIBS[i];
      var q = rot(x - F.x, y - F.y, -F.r);
      var h = flower(q[0] / F.s, q[1] / F.s, o, F.col);
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

  var cols = 0, rows = 0, cw = 6, lh = 11;
  function measure() {
    var probe = document.createElement('span');
    probe.textContent = 'MMMMMMMMMM';
    pre.appendChild(probe);
    cw = probe.getBoundingClientRect().width / 10;
    pre.removeChild(probe);
    var cs = getComputedStyle(pre);
    lh = parseFloat(cs.lineHeight) || cw * 1.8;
    var padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
    var padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    cols = Math.max(20, Math.floor((pre.clientWidth - padX - 1) / cw));
    rows = Math.max(16, Math.floor((pre.clientHeight - padY - 1) / lh));
  }

  function esc(ch) {
    return ch === '<' ? '&lt;' : ch === '>' ? '&gt;' : ch === '&' ? '&amp;' : ch;
  }

  var T0 = -0.65;            // intro starts zoomed out on the bouquet
  var IDLE = -0.03;          // the bouquet rests here, fully open, until clicked
  function frame(t, tick) {
    var n = Math.floor(t);
    var off = Math.max(0, n - 2);      // renormalise so floats never underflow
    var tl = t - off;
    var ctx = {
      maxD: Math.floor(tl) + 3,
      col: off,
      open: function (d) { return smooth(tl - d + 1); },
      // a flower fades into background texture once its bud takes over the frame
      fade: function (d) { return 0.28 + 0.72 * smooth(1 - (tl - d - 0.15) / 0.75); }
    };
    var scale = Math.pow(S, tl), ang = tl >= 0 ? PHI * tl : 0;
    var intro = smooth(-tl / -T0);
    var half = 1.25;
    var R = Math.min(cols * cw, rows * lh) / 2;   // the flower fits the shorter side
    var out = [], last = '', run = '';
    var shift = Math.floor(tick / 5);
    for (var row = 0; row < rows; row++) {
      for (var c = 0; c < cols; c++) {
        var qx = (c - cols / 2 + 0.5) * cw / R * half;
        var qy = (rows / 2 - row - 0.5) * lh / R * half;
        var wx, wy;
        if (tl >= 0) {
          var d = rot(qx - FP[0], qy - FP[1], ang);
          wx = FP[0] + scale * d[0]; wy = FP[1] + scale * d[1];
        } else {
          wx = qx * scale; wy = qy * scale - 1.1 * intro;
        }
        var hit = level(wx, wy, 0, ctx);
        if (!hit && off === 0 && tl < 1.2) hit = rootExtras(wx, wy, ctx.open(0));
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

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  measure();
  window.addEventListener('resize', function () { measure(); if (reduce) frame(t, 0); });

  // State: the bouquet opens and rests at IDLE. Bloom.zoom() falls into a petal,
  // calls back once the first bud has opened, then keeps zooming slowly forever.
  var t = reduce ? IDLE : T0, mode = 'idle', zoomFrom = 0, onArrive = null, tick = 0;
  var api = window.Bloom = {
    zoom: function (cb) {
      if (mode === 'zoom') return;
      if (reduce) { cb && cb(); return; }
      mode = 'zoom'; zoomFrom = Math.max(t, IDLE); onArrive = cb || null;
    },
    reset: function () { mode = 'idle'; t = T0; onArrive = null; if (reduce) frame(t, 0); },
    get zooming() { return mode === 'zoom'; },
    seek: function (x) { t = x; frame(t, tick); }   // handy for debugging a single frame
  };

  if (reduce) { frame(t, 0); return; }

  var visible = true, lastDraw = null;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(pre);
  }
  function loop(now) {
    requestAnimationFrame(loop);
    if (!visible || document.hidden) { lastDraw = null; return; }
    if (lastDraw !== null && now - lastDraw < 33) return;
    var dt = lastDraw === null ? 0 : Math.min(now - lastDraw, 100) / 1000;
    lastDraw = now;
    tick++;
    if (mode === 'idle') {
      t = Math.min(IDLE, t + dt * 0.16);
    } else {
      var p = t - zoomFrom;
      // ease in, rush through the first bud, then settle into a slow drift
      var v = p < 1.7 ? 0.12 + 0.5 * smooth(p / 0.6) : 0.1;
      t += dt * v;
      if (onArrive && p >= 1.7) { var f = onArrive; onArrive = null; f(); }
    }
    frame(t, tick);
  }
  requestAnimationFrame(loop);
})();
