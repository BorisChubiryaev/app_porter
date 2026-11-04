// The page's toys. Everything readable is in the HTML; without this file only the toys stop.
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function load(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function save(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }
  function pad(n, width) { return String(n).padStart(width, '0'); }

  document.querySelectorAll('.lang a').forEach(function (a) {
    a.addEventListener('click', function () { save('lang', a.getAttribute('hreflang')); });
  });

  // ---- the level in the hero: a cartridge runs, jumps over bugs and picks up coins
  var box = document.getElementById('game');
  var canvas = box.querySelector('canvas');
  var ctx = canvas.getContext('2d');
  var msg = document.getElementById('game-msg');
  var scoreEl = document.getElementById('game-score');
  var bestEl = document.getElementById('game-best');
  var SCALE = 4, HEIGHT = 65, GROUND = 52, GRAVITY = 620, JUMP = -205;

  var art = {};
  Object.keys(NX_SPRITES.sprites).forEach(function (name) {
    var rows = NX_SPRITES.sprites[name];
    var c = document.createElement('canvas');
    c.width = rows[0].length; c.height = rows.length;
    var g = c.getContext('2d');
    rows.forEach(function (row, y) {
      for (var x = 0; x < row.length; x++) {
        if (row[x] === '.') continue;
        g.fillStyle = NX_SPRITES.palette[row[x]];
        g.fillRect(x, y, 1, 1);
      }
    });
    art[name] = c;
  });

  // Chips on the horizon, from a fixed list so that the skyline repeats without a seam
  var SKYLINE = [[0, 22, 16], [34, 14, 26], [60, 30, 12], [104, 18, 22], [136, 12, 32], [160, 34, 18], [210, 16, 14], [240, 24, 28], [280, 20, 16]];
  var PERIOD = 320;

  var mode = 'demo', width = 320, last = 0, running = false, visible = true;
  var y = 0, vy = 0, x = 0, score = 0, best = parseInt(load('best') || '0', 10) || 0, speed = 80, travelled = 0, spawn = 0, things = [], overAt = 0;

  function say(key) { msg.textContent = box.dataset[key]; }
  function showScore() { scoreEl.textContent = pad(score, 3); bestEl.textContent = pad(best, 3); }

  function fit() {
    width = Math.max(120, Math.ceil(box.clientWidth / SCALE));
    canvas.width = width; canvas.height = HEIGHT;
    ctx.imageSmoothingEnabled = false;
    x = Math.max(14, Math.floor(width * 0.14));
  }

  function reset(next) {
    mode = next; y = 0; vy = 0; score = 0; speed = 80; spawn = 0.5; things = [];
    say(next === 'play' ? 'go' : 'demo');
    showScore();
  }

  function jump() { if (y === 0) vy = JUMP; }

  function hit(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function step(dt) {
    travelled += speed * dt;
    speed = Math.min(165, speed + dt * 2.2);
    vy += GRAVITY * dt;
    y = Math.min(0, y + vy * dt);
    if (y === 0) vy = 0;

    spawn -= dt;
    if (spawn <= 0) {
      if (Math.random() < 0.62) things.push({ kind: 'bug', x: width + 4, y: GROUND - 8, w: 10, h: 8 });
      else things.push({ kind: 'coin', x: width + 4, y: GROUND - (Math.random() < 0.5 ? 14 : 34), w: 10, h: 10 });
      spawn = 0.55 + Math.random() * 0.75;
    }
    var me = { x: x + 2, y: GROUND - 14 + y + 1, w: 8, h: 12 };
    things = things.filter(function (t) {
      t.x -= speed * dt;
      if (t.x < -12) return false;
      if (mode === 'demo' && t.kind === 'bug' && y === 0 && t.x - x < speed * 0.2 && t.x > x) jump();
      if (!hit(me, t)) return true;
      if (t.kind === 'coin') {
        if (mode === 'play') { score += 1; if (score > best) { best = score; save('best', String(best)); } showScore(); }
        return false;
      }
      if (mode === 'play') { mode = 'over'; overAt = performance.now(); say('over'); }
      return mode !== 'demo';
    });
  }

  function draw() {
    ctx.clearRect(0, 0, width, HEIGHT);
    // the skyline drifts slower than the ground
    var drift = (travelled * 0.25) % PERIOD;
    for (var t = -1; t * PERIOD < width + PERIOD; t++) {
      SKYLINE.forEach(function (b) {
        var bx = Math.round(t * PERIOD + b[0] - drift), top = GROUND - b[2];
        ctx.fillStyle = '#2a1fc4';
        ctx.fillRect(bx, top, b[1], b[2]);
        ctx.fillStyle = '#3a2be8';
        for (var i = 2; i < b[1] - 1; i += 4) ctx.fillRect(bx + i, top + 2, 2, 2);
      });
    }
    // the ground is a circuit board
    ctx.fillStyle = '#15104a';
    ctx.fillRect(0, GROUND, width, HEIGHT - GROUND);
    ctx.fillStyle = '#ffd23f';
    var off = Math.floor(travelled) % 16;
    for (var gx = -off; gx < width; gx += 16) ctx.fillRect(gx, GROUND + 3, 8, 1);
    ctx.fillStyle = '#2ee6a6';
    var off2 = Math.floor(travelled) % 28;
    for (var gx2 = -off2; gx2 < width; gx2 += 28) ctx.fillRect(gx2, GROUND + 8, 2, 2);

    things.forEach(function (t) { ctx.drawImage(art[t.kind], Math.round(t.x), Math.round(t.y)); });
    var frame = y < 0 ? art.hero_j : (Math.floor(travelled / 7) % 2 ? art.hero_a : art.hero_b);
    ctx.drawImage(frame, x, Math.round(GROUND - 14 + y));
  }

  function tick(now) {
    if (!running) return;
    var dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (mode !== 'over') step(dt);
    else if (now - overAt > 7000) reset('demo');
    draw();
    requestAnimationFrame(tick);
  }

  function run(on) {
    if (on === running) return;
    running = on;
    if (on) { last = performance.now(); requestAnimationFrame(tick); }
  }

  function wanted() { return visible && !document.hidden && (!reduce || mode !== 'demo'); }

  function press() {
    if (mode === 'demo') { reset('play'); run(wanted()); jump(); }
    else if (mode === 'play') jump();
    else if (performance.now() - overAt > 350) { reset('play'); jump(); }
  }

  // A swipe that scrolls the page over the level must not start a game, so the start waits for a click
  box.addEventListener('pointerdown', function () { if (mode === 'play') jump(); });
  box.addEventListener('click', function () { if (mode !== 'play') press(); });
  box.addEventListener('keydown', function (e) {
    if (e.code === 'Space' || e.code === 'Enter' || e.code === 'ArrowUp') { e.preventDefault(); press(); }
  });
  document.addEventListener('keydown', function (e) {
    if (mode !== 'play' || e.target === box) return;
    if ((e.code === 'Space' || e.code === 'ArrowUp') && !/^(INPUT|BUTTON|A|SUMMARY|TEXTAREA|SELECT)$/.test(e.target.tagName)) { e.preventDefault(); jump(); }
  });

  fit(); showScore(); draw();
  addEventListener('resize', function () { fit(); draw(); });
  new IntersectionObserver(function (entries) { visible = entries[0].isIntersecting; run(wanted()); }).observe(box);
  document.addEventListener('visibilitychange', function () { run(wanted()); });

  // ---- the cartridge that walks the stage map as the page scrolls
  var how = document.getElementById('how'), rail = how.querySelector('.rail'), walker = how.querySelector('.walker');
  var queued = false;
  function walk() {
    queued = false;
    var r = how.getBoundingClientRect(), h = innerHeight;
    var p = Math.max(0, Math.min(1, (h * 0.75 - r.top) / (r.height + h * 0.1)));
    rail.style.setProperty('--p', p.toFixed(4));
    walker.style.setProperty('--p', p.toFixed(4));
    walker.dataset.f = Math.floor(p * 40) % 2;
  }
  addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(walk); } }, { passive: true });
  walk();

  // ---- the practice screen: the same choices as the game's on-screen buttons
  var screen = document.querySelector('#phone .screen');
  var buttons = Array.prototype.slice.call(screen.querySelectorAll('button'));
  function place(b, px, py) {
    var maxX = 100 - (b.offsetWidth / screen.clientWidth) * 100, maxY = 100 - (b.offsetHeight / screen.clientHeight) * 100;
    px = Math.max(0, Math.min(maxX, px)); py = Math.max(0, Math.min(maxY, py));
    b.dataset.nowX = px; b.dataset.nowY = py;
    b.style.left = px + '%'; b.style.top = py + '%';
  }
  function home() { buttons.forEach(function (b) { place(b, +b.dataset.x, +b.dataset.y); }); }
  buttons.forEach(function (b) {
    b.addEventListener('pointerdown', function (e) {
      b.setPointerCapture(e.pointerId);
      b.classList.add('drag');
      var r = screen.getBoundingClientRect(), sx = e.clientX, sy = e.clientY, ox = +b.dataset.nowX, oy = +b.dataset.nowY;
      function move(ev) { place(b, ox + (ev.clientX - sx) / r.width * 100, oy + (ev.clientY - sy) / r.height * 100); }
      function up() { b.classList.remove('drag'); b.removeEventListener('pointermove', move); b.removeEventListener('pointerup', up); b.removeEventListener('pointercancel', up); }
      b.addEventListener('pointermove', move); b.addEventListener('pointerup', up); b.addEventListener('pointercancel', up);
    });
    b.addEventListener('keydown', function (e) {
      var d = { ArrowLeft: [-2, 0], ArrowRight: [2, 0], ArrowUp: [0, -4], ArrowDown: [0, 4] }[e.key];
      if (!d) return;
      e.preventDefault();
      place(b, +b.dataset.nowX + d[0], +b.dataset.nowY + d[1]);
    });
  });
  var size = document.getElementById('ctl-size'), opacity = document.getElementById('ctl-opacity'), hide = document.getElementById('ctl-hide');
  size.addEventListener('input', function () { screen.style.setProperty('--s', size.value / 100); });
  opacity.addEventListener('input', function () { screen.style.setProperty('--o', opacity.value / 100); });
  hide.addEventListener('change', function () { screen.classList.toggle('off', hide.checked); });
  document.getElementById('ctl-reset').addEventListener('click', function () {
    size.value = 100; opacity.value = 100; hide.checked = false;
    screen.style.setProperty('--s', 1); screen.style.setProperty('--o', 1); screen.classList.remove('off');
    home();
  });
  home();
  addEventListener('resize', home);

  // ---- the toy coin: a sound and a counter, and no money anywhere near it
  var coin = document.getElementById('coin'), credit = document.getElementById('credit'), coins = 0, audio = null;
  function blip() {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      [[880, 0], [1175, 0.08]].forEach(function (n) {
        var o = audio.createOscillator(), g = audio.createGain(), at = audio.currentTime + n[1];
        o.type = 'square'; o.frequency.value = n[0];
        g.gain.setValueAtTime(0.05, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.22);
        o.connect(g); g.connect(audio.destination); o.start(at); o.stop(at + 0.22);
      });
    } catch (e) {}
  }
  coin.addEventListener('click', function () {
    if (coin.classList.contains('in')) return;
    coins = Math.min(99, coins + 1);
    credit.textContent = pad(coins, 2);
    blip();
    coin.classList.add('in');
    setTimeout(function () { coin.classList.remove('in'); }, reduce ? 0 : 500);
  });

  // ---- for those who try the old code
  var code = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'], at = 0;
  addEventListener('keydown', function (e) {
    at = e.key === code[at] ? at + 1 : (e.key === code[0] ? 1 : 0);
    if (at === code.length) { at = 0; document.documentElement.classList.toggle('crt'); }
  });
})();
