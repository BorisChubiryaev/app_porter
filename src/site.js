// The page's toys. Everything readable is in the HTML; without this file only the toys stop.
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function load(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function save(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }

  document.querySelectorAll('.lang a').forEach(function (a) {
    a.addEventListener('click', function () { save('lang', a.getAttribute('hreflang')); });
  });

  // ---- the scene under the hero: a cartridge runs and jumps over bugs by itself; it takes no input
  var box = document.getElementById('scene');
  var canvas = box.querySelector('canvas');
  var ctx = canvas.getContext('2d');
  var SCALE = 4, HEIGHT = 65, GROUND = 52, GRAVITY = 620, JUMP = -205, SPEED = 80;

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

  var width = 320, last = 0, running = false, visible = true;
  var y = 0, vy = 0, x = 0, travelled = 0, spawn = 0.5, bugs = [];

  function fit() {
    width = Math.max(120, Math.ceil(box.clientWidth / SCALE));
    canvas.width = width; canvas.height = HEIGHT;
    ctx.imageSmoothingEnabled = false;
    x = Math.max(14, Math.floor(width * 0.14));
  }

  function step(dt) {
    travelled += SPEED * dt;
    vy += GRAVITY * dt;
    y = Math.min(0, y + vy * dt);
    if (y === 0) vy = 0;
    spawn -= dt;
    if (spawn <= 0) { bugs.push(width + 4); spawn = 1 + Math.random() * 1.5; }
    bugs = bugs.map(function (b) { return b - SPEED * dt; }).filter(function (b) { return b > -12; });
    if (y === 0 && bugs.some(function (b) { return b > x && b - x < SPEED * 0.3; })) vy = JUMP;
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

    bugs.forEach(function (b) { ctx.drawImage(art.bug, Math.round(b), GROUND - 8); });
    var frame = y < 0 ? art.hero_j : (Math.floor(travelled / 7) % 2 ? art.hero_a : art.hero_b);
    ctx.drawImage(frame, x, Math.round(GROUND - 14 + y));
  }

  function tick(now) {
    if (!running) return;
    step(Math.min(0.05, (now - last) / 1000));
    last = now;
    draw();
    requestAnimationFrame(tick);
  }

  function run(on) {
    if (on === running) return;
    running = on;
    if (on) { last = performance.now(); requestAnimationFrame(tick); }
  }

  function wanted() { return visible && !document.hidden && !reduce; }

  fit(); draw();
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

  // ---- for those who try the old code
  var code = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'], at = 0;
  addEventListener('keydown', function (e) {
    at = e.key === code[at] ? at + 1 : (e.key === code[0] ? 1 : 0);
    if (at === code.length) { at = 0; document.documentElement.classList.toggle('crt'); }
  });
})();
