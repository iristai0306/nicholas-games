/* DISTORTED — PC-only gate.
   Shows a "PC only" screen on phones/tablets (touch + small screen).
   Include with: <script src="pc-gate.js"></script> just before </body>. */
(function () {
  function touchLike() {
    try {
      var mq = window.matchMedia;
      var coarse = mq && mq('(pointer: coarse)').matches;
      var noHover = mq && mq('(hover: none)').matches;
      var touch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
      var sw = (window.screen && screen.width) || 9999;
      var sh = (window.screen && screen.height) || 9999;
      var small = Math.min(sw, sh) < 820;
      return (coarse && noHover) || (touch && small);
    } catch (e) { return false; }
  }

  function inject() {
    if (document.getElementById('pcgate')) return;
    var st = document.createElement('style');
    st.textContent =
      "#pcgate{position:fixed;inset:0;z-index:99999;background:radial-gradient(ellipse at 50% 28%,#241547 0%,#0a0a12 70%);" +
      "color:#fff;display:flex;align-items:center;justify-content:center;padding:26px;text-align:center;" +
      "font-family:'Rajdhani','Trebuchet MS',system-ui,sans-serif;-webkit-user-select:none;user-select:none}" +
      "#pcgate .pcg{max-width:600px}" +
      "#pcgate .emoji{font-size:52px;display:block;margin-bottom:8px}" +
      "#pcgate h2{letter-spacing:4px;font-size:clamp(21px,6.5vw,32px);margin-bottom:12px;font-weight:900}" +
      "#pcgate h2 span{color:#a855f7}" +
      "#pcgate p{opacity:.85;line-height:1.55;font-size:15px;margin-bottom:7px}" +
      "#pcgate .keys{margin:20px 0 4px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center}" +
      "#pcgate .k{border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:7px 13px;font-size:12.5px;" +
      "letter-spacing:1.5px;color:#cfe9f5;background:rgba(255,255,255,.05)}" +
      "#pcgate button{margin-top:22px;font-family:inherit;font-weight:700;letter-spacing:2px;font-size:12.5px;" +
      "color:#8899bb;background:none;border:1px solid rgba(255,255,255,.14);border-radius:8px;padding:9px 20px;cursor:pointer}" +
      "#pcgate button:hover{color:#fff;border-color:rgba(255,255,255,.4)}";
    document.head.appendChild(st);

    var o = document.createElement('div');
    o.id = 'pcgate';
    o.innerHTML =
      '<div class="pcg">' +
      '<span class="emoji">\uD83D\uDDA5\uFE0F</span>' +
      '<h2>DISTORTED IS <span>PC ONLY</span></h2>' +
      '<p>This game needs a computer with a keyboard and mouse.</p>' +
      '<p>Open it on a PC and you\u2019re in.</p>' +
      '<div class="keys"><span class="k">WASD \u2014 move</span><span class="k">MOUSE \u2014 look</span>' +
      '<span class="k">SCROLL \u2014 zoom</span></div>' +
      '<button id="pcgGo">Continue anyway (not recommended)</button>' +
      '</div>';
    document.body.appendChild(o);
    document.getElementById('pcgGo').onclick = function () {
      if (o.parentNode) o.parentNode.removeChild(o);
    };
  }

  if (touchLike()) {
    if (document.body) inject();
    else document.addEventListener('DOMContentLoaded', inject);
  }
})();
