/* ════════════════════════════════════════════════════════════════════════════
   FILAMENT — visual engine.  One pure function:  draw(gl, t)
   The image at time t is a function of (t, score events, telemetry) only.
   Integrations that need history (hand position, warmth, camera travel, telemetry
   smoothing) are precomputed ONCE at init into constant tables sampled by t, so no
   state is carried from frame to frame; any frame can be drawn in any order.
   All pixels come from a raymarched SDF scene (fBM + domain repetition) and a post
   pass (chromatic aberration on pick transients, film grain from a hash, tonemap).
   ════════════════════════════════════════════════════════════════════════════ */
(function (global) {
'use strict';

const ZB = 2.0, ZN = 40.0, SY = 1.62, SPACING = 0.22, ROWS = 31, SX = 1.6, SZ = 2.2, Z0 = -8.0;
const KEY_ROW = 15;                           // the voice tube: left inner column, row 15 (pitch class A)
const KEY_POS = [-0.8, 0.7, Z0 + KEY_ROW * SZ];
const zOfFret = f => ZB + (ZN - ZB) * Math.pow(2, -f / 12);
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const mix = (a, b, u) => a + (b - a) * u;
const smooth = (a, b, x) => { const u = clamp((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u); };
const ease = (c, u) => c === 'lin' ? u : c === 'smooth' ? u * u * (3 - 2 * u) : 1 - Math.pow(1 - u, 2.2);

// ─── Shaders ──────────────────────────────────────────────────────────────────
const VS = `#version 300 es
in vec2 a; out vec2 v_uv;
void main(){ v_uv = a * 0.5 + 0.5; gl_Position = vec4(a, 0.0, 1.0); }`;

const FS_SCENE = `#version 300 es
precision highp float;
in vec2 v_uv; out vec4 o;
uniform vec2 u_res;
uniform float u_time, u_rms, u_sub_bass, u_lead_transients, u_highs, u_attack_transient;
uniform vec3 u_camPos, u_camTgt; uniform float u_fov;
uniform float u_pc[12];
uniform vec4 u_n0[4];   // string index, z of fret, glow, lateral deflection
uniform vec4 u_n1[4];   // vibration amp, vibration phase, spread width, velocity
uniform float u_field, u_key, u_heat, u_tension, u_haze, u_band, u_molten, u_spread, u_pressure, u_exposure;
uniform vec3 u_wave;    // radius, strength, active
uniform float u_cool;   // cooling radius around the voice tube (large = none)

const float ZB = ${ZB.toFixed(2)}, ZN = ${ZN.toFixed(2)}, SY = ${SY.toFixed(3)}, SP = ${SPACING.toFixed(3)};
const float SX = ${SX.toFixed(2)}, SZ = ${SZ.toFixed(2)}, Z0 = ${Z0.toFixed(2)};
const float ROWS = ${ROWS.toFixed(1)}, KEYROW = ${KEY_ROW.toFixed(1)};
const vec3 KEYPOS = vec3(${KEY_POS.map(v => v.toFixed(3)).join(',')});

float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float n2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++){ s += a * n2(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return s; }

vec3 blackbody(float x){          // x: 0 = dull ember … 1 = white-hot
  x = clamp(x, 0.0, 1.0);
  vec3 ember = vec3(0.48, 0.07, 0.012), amber = vec3(1.0, 0.43, 0.07), gold = vec3(1.0, 0.72, 0.30), white = vec3(1.0, 0.93, 0.80);
  return x < 0.35 ? mix(ember, amber, x / 0.35) : x < 0.7 ? mix(amber, gold, (x - 0.35) / 0.35) : mix(gold, white, (x - 0.7) / 0.3);
}

float sdCyl(vec3 p, float r, float h0, float h1){ vec2 d = vec2(length(p.xz) - r, max(h0 - p.y, p.y - h1)); return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)); }
float sdBox(vec3 p, vec3 b){ vec3 q = abs(p) - b; return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0); }

// domain repetition: two mirrored banks of tube columns either side of the aisle
vec3 cell(vec3 p, out vec2 id){
  float side = p.x < 0.0 ? -1.0 : 1.0;
  float ax = abs(p.x) - 0.8;
  float k = clamp(floor(ax / SX + 0.5), 0.0, 4.0);
  float r = clamp(floor((p.z - Z0) / SZ + 0.5), 0.0, ROWS - 1.0);
  id = vec2(side * (k + 1.0), r);
  return vec3(ax - k * SX, p.y, p.z - (Z0 + r * SZ));
}

// current through one tube: chord pitch classes (rows in circle-of-fifths order), spread, voice tube, ignition wave, cooling
float tubeI(vec2 id){
  float k = abs(id.x) - 1.0, r = id.y;
  int pc = int(mod(r * 7.0, 12.0));
  float chord = u_pc[pc];
  float reach = smoothstep(k * 0.24 - 0.06, k * 0.24 + 0.12, u_spread);
  float I = chord * reach * (1.0 - 0.12 * k);
  vec3 c = vec3(sign(id.x) * (0.8 + k * SX), 0.7, Z0 + r * SZ);
  if (id.x < 0.0 && k < 0.5 && abs(r - KEYROW) < 0.5) I = max(I, u_key);
  if (u_wave.z > 0.5) {
    float dist = length(c - vec3(0.0, SY, ${zOfFret(15).toFixed(3)}));
    float lit = smoothstep(u_wave.x, u_wave.x - 3.0, dist);
    float front = exp(-pow((dist - u_wave.x) / 1.6, 2.0));
    I = max(I, u_wave.y * (0.55 * lit + 0.6 * front) * (1.0 - 0.06 * k) * (0.85 + 0.3 * h21(id)));
  }
  float dk = length(c - KEYPOS);
  I *= smoothstep(u_cool, u_cool - 4.0, dk);
  return clamp(I, 0.0, 1.4);
}

float stringX(float s){ return (2.5 - s) * SP; }
float stringR(float s){ return mix(0.0055, 0.011, s / 5.0); }

// displacement of string s at z from every active lead note on that string
vec2 stringOffset(float s, float z){
  vec2 d = vec2(0.0);
  for (int i = 0; i < 4; i++){
    vec4 a = u_n0[i]; vec4 b = u_n1[i];
    if (a.z <= 0.0 || abs(a.x - s) > 0.5) continue;
    float zf = a.y;
    float tri = z < zf ? clamp((z - ZB) / max(0.01, zf - ZB), 0.0, 1.0) : clamp((ZN - z) / max(0.01, ZN - zf), 0.0, 1.0);
    d.x += a.w * tri;
    float u = clamp((z - ZB) / max(0.01, zf - ZB), 0.0, 1.0);
    d.y += b.x * sin(3.14159 * u) * sin(b.y) * (z < zf ? 1.0 : 0.0);
  }
  return d;
}
float sdString(vec3 p, float s){
  vec2 off = stringOffset(s, p.z);
  vec2 c = vec2(stringX(s) + off.x, SY + off.y);
  float along = max(ZB - p.z, p.z - ZN);
  float r = max(stringR(s), length(p - u_camPos) * 0.0011);   // never thinner than ~1 px: no shimmer
  return max(length(p.xy - c) - r, along);
}
float sdStrings(vec3 p, out float sid){
  float sc = clamp(floor(2.5 - p.x / SP + 0.5), 0.0, 5.0);
  float best = 1e9; sid = sc;
  for (int j = -1; j <= 1; j++){
    float s = sc + float(j); if (s < 0.0 || s > 5.0) continue;
    float d = sdString(p, s); if (d < best){ best = d; sid = s; }
  }
  return best;
}

// materials: 1 floor, 2 socket, 3 plate, 4 string, 5 bridge/nut
float scene(vec3 p, out float mat, out vec2 id, out float sid, out float dGlass, out float dFil){
  vec3 q = cell(p, id);
  float dSock = sdCyl(q, 0.3, 0.0, 0.17) - 0.01;
  float dPlate = sdBox(vec3(abs(q.x) - 0.1, q.y - 0.72, q.z), vec3(0.01, 0.25, 0.085));                 // two plates, filament between
  dPlate = min(dPlate, sdBox(vec3(q.x, abs(q.y - 0.72) - 0.27, q.z), vec3(0.14, 0.004, 0.1)));             // mica spacers
  dGlass = min(sdCyl(q, 0.24, 0.16, 1.18), length(q - vec3(0.0, 1.18, 0.0)) - 0.24);
  dFil = length(q - vec3(0.0, clamp(q.y, 0.42, 1.0), 0.0));
  float dStr = (abs(p.y - SY) < 0.6 && abs(p.x) < 1.1) ? sdStrings(p, sid) : max(abs(p.y - SY) - 0.5, abs(p.x) - 1.0);
  if (abs(p.y - SY) >= 0.6 || abs(p.x) >= 1.1) sid = clamp(floor(2.5 - p.x / SP + 0.5), 0.0, 5.0);
  float dBr = min(sdBox(p - vec3(0.0, SY - 0.06, ZB - 0.05), vec3(0.72, 0.05, 0.06)), sdBox(p - vec3(0.0, SY - 0.06, ZN + 0.05), vec3(0.72, 0.05, 0.06)));
  float d = p.y; mat = 1.0;
  if (dSock < d){ d = dSock; mat = 2.0; }
  if (dPlate < d){ d = dPlate; mat = 3.0; }
  if (dStr < d){ d = dStr; mat = 4.0; }
  if (dBr < d){ d = dBr; mat = 5.0; }
  return d;
}

float strGlowAt(vec3 p, float sid, out vec3 col){
  // strike points (incl. the light flowing along the ringing string) + molten sheen
  float g = 0.0; col = vec3(0.0);
  for (int i = 0; i < 4; i++){
    vec4 a = u_n0[i]; vec4 b = u_n1[i];
    if (a.z <= 0.0) continue;
    vec2 off = stringOffset(a.x, p.z);
    float dl = length(p.xy - vec2(stringX(a.x) + off.x, SY + off.y));
    float w = b.z;
    float along = exp(-pow((p.z - a.y) / w, 2.0)) + 0.25 * exp(-abs(p.z - a.y) / (w * 3.0)) * step(p.z, a.y);
    float e = a.z * along / (1.0 + pow(dl / 0.02, 2.0));
    g += e; col += e * blackbody(0.55 + 0.45 * b.w);
  }
  if (u_molten > 0.0){
    vec2 off = stringOffset(sid, p.z);
    float dl = length(p.xy - vec2(stringX(sid) + off.x, SY + off.y));
    float flow = fbm(vec2(p.z * 0.9 - u_time * 1.7, sid * 3.1)) ;
    float e = u_molten * (0.25 + flow * flow) * 0.25 / (1.0 + pow(dl / 0.009, 2.0)) * step(ZB, p.z) * step(p.z, ZN);
    g += e; col += e * blackbody(0.35 + 0.4 * flow);
  }
  return g;
}

vec3 normalAt(vec3 p){
  float m; vec2 id; float s, g, f; vec2 e = vec2(0.0015, 0.0);
  return normalize(vec3(scene(p + e.xyy, m, id, s, g, f) - scene(p - e.xyy, m, id, s, g, f),
                        scene(p + e.yxy, m, id, s, g, f) - scene(p - e.yxy, m, id, s, g, f),
                        scene(p + e.yyx, m, id, s, g, f) - scene(p - e.yyx, m, id, s, g, f)));
}

const vec3 FOG = vec3(0.0045, 0.0036, 0.0052);
const vec3 MOON = vec3(0.07, 0.062, 0.11);

// march accumulating emissive light (filaments, strings, glass rims); returns hit distance or -1
float march(vec3 ro, vec3 rd, float tmax, int steps, out vec3 acc, out float mat, out vec2 hid, out float hsid, out float trans){
  acc = vec3(0.0); float t = 0.02; mat = 0.0; hid = vec2(0.0); hsid = 0.0; trans = 1.0; float prevDg = 1.0; vec2 prevId = vec2(-99.0);
  for (int i = 0; i < 200; i++){
    if (i >= steps || t > tmax) break;
    vec3 p = ro + rd * t;
    float m; vec2 id; float sid, dg, df;
    float d = scene(p, m, id, sid, dg, df);
    float I = tubeI(id);
    float stepLen = min(d, max(abs(dg) + 0.01, 0.02));
    stepLen = min(stepLen, max(df * 0.7, 0.015));
    vec3 q = cell(p, id);
    if (I > 0.002){
      vec3 tc = blackbody(0.3 + 0.55 * I + 0.25 * u_pressure);
      float core = I * I * 0.004 / (df * df + 0.0004);
      float glow = I * 2.2 * exp(-df * 16.0) * step(dg, 0.0);
      float scatter = I * 0.0045 / (1.0 + df * df * 3.0);
      acc += tc * (core + glow + scatter) * stepLen * trans;
    }
    if (id == prevId && dg * prevDg < 0.0){
      vec3 nG = q.y > 1.18 ? normalize(q - vec3(0.0, 1.18, 0.0)) : normalize(vec3(q.x, 0.0, q.z) + 1e-5);
      float cs = abs(dot(rd, nG)), fres = 0.03 + 0.97 * pow(1.0 - cs, 5.0);
      vec3 refl = MOON * 0.55 + blackbody(0.45 + 0.4 * I) * I * 0.5 + vec3(0.9, 0.86, 0.8) * u_highs * u_band * 0.2 * pow(1.0 - cs, 3.0);
      acc += refl * fres * trans;
      trans *= 0.95;
    }
    prevDg = dg; prevId = id;
    if (abs(p.y - SY) < 0.7 && abs(p.x) < 1.2 && p.z > ZB - 1.0 && p.z < ZN + 1.0){ vec3 sc; float sg = strGlowAt(p, sid, sc); acc += sc * 0.9 * stepLen * trans; }
    if (d < 0.0008 * t + 0.0004){ mat = m; hid = id; hsid = sid; return t; }
    t += stepLen * 0.92;
  }
  return -1.0;
}

vec3 shade(vec3 p, vec3 rd, float mat, vec2 id, float sid, vec3 n){
  vec3 q = cell(p, id);
  float I = tubeI(id);
  vec3 fp = vec3(sign(id.x) * (0.8 + (abs(id.x) - 1.0) * SX), clamp(p.y, 0.42, 1.0), Z0 + id.y * SZ);
  vec3 L = fp - p; float dl = length(L); L /= dl;
  vec3 tubeCol = blackbody(0.3 + 0.55 * I + 0.25 * u_pressure);
  float diff = max(dot(n, L), 0.0);
  vec3 lit = tubeCol * I * diff * 0.9 / (1.0 + 7.0 * dl * dl);
  vec3 moonDir = normalize(vec3(0.3, 1.0, -0.25));
  float md = max(dot(n, moonDir), 0.0);
  vec3 h = normalize(moonDir - rd);
  float ms = pow(max(dot(n, h), 0.0), 60.0);
  float ambient = 0.012 + 0.05 * u_rms * u_band;
  vec3 c;
  if (mat < 1.5) {                       // floor: obsidian (handled with reflection by caller)
    c = vec3(0.006, 0.005, 0.008) + lit * 0.25 + MOON * md * 0.06;
  } else if (mat < 2.5) {                // bakelite socket
    c = vec3(0.03, 0.018, 0.012) * (ambient * 4.0 + md * 0.4) + lit * vec3(0.35, 0.25, 0.2) + MOON * ms * 0.25;
  } else if (mat < 3.5) {                // plate: dark nickel, red-plating when driven
    float mott = fbm(q.xy * 9.0 + vec2(u_time * 0.21, 0.0));
    float redp = u_heat * smoothstep(0.3, 1.0, I) * smoothstep(0.25, 0.75, mott);
    c = vec3(0.035, 0.033, 0.036) * (ambient * 3.0 + md * 0.35) + lit * 0.35 + blackbody(0.04 + 0.22 * redp) * redp * 0.55;
  } else if (mat < 4.5) {                // liquid-metal string
    float flow = fbm(vec2(p.z * 3.0 - u_time * 0.9, sid * 2.0 + atan(n.y, n.x)));
    vec3 r = reflect(rd, n);
    float spec = pow(max(dot(r, moonDir), 0.0), 30.0);
    float tspec = pow(max(dot(r, L), 0.0), 8.0) * I / (1.0 + 2.0 * dl * dl);
    vec3 gold = vec3(0.95, 0.68, 0.36);
    float sheen = u_field * smoothstep(0.35, -0.6, r.y);          // the lit field below, seen in the metal
    c = gold * (0.02 + 0.35 * spec * (0.4 + u_lead_transients) + 1.1 * tspec + 0.55 * sheen) * (0.75 + 0.5 * flow);
    vec3 sc; float sg = strGlowAt(p, sid, sc); c += sc * 1.5;
  } else {                               // bridge / nut
    c = vec3(0.02, 0.018, 0.02) * (ambient * 4.0 + md * 0.6) + lit * 0.4 + MOON * ms * 0.3;
  }
  return c;
}

void main(){
  vec2 uv = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;
  // heat haze: the air itself bends when the amp is driven
  if (u_haze > 0.0) uv += u_haze * 0.0035 * (vec2(fbm(uv * 5.0 + vec2(0.0, -u_time * 1.3)), fbm(uv * 5.0 + vec2(4.0, -u_time * 1.1))) - 0.5) * smoothstep(0.6, -0.2, uv.y);
  vec3 ro = u_camPos, fw = normalize(u_camTgt - u_camPos), rt = normalize(cross(fw, vec3(0, 1, 0))), up = cross(rt, fw);
  float f = 1.0 / tan(radians(u_fov) * 0.5);
  vec3 rd = normalize(fw * f + uv.x * rt + uv.y * up);
  vec3 acc; float mat; vec2 id; float sid; float trans;
  float t = march(ro, rd, 80.0, 150, acc, mat, id, sid, trans);
  vec3 col = vec3(0.0);
  float fogT = t < 0.0 ? 80.0 : t;
  float fogAmt = 1.0 - exp(-0.03 * fogT);
  if (t > 0.0){
    vec3 p = ro + rd * t;
    vec3 n = normalAt(p);
    if (mat < 1.5){
      // obsidian mirror: fBM micro-relief + sub-bass ripple rings, fresnel reflection
      float rip = sin(length(p.xz - vec2(0.0, 24.0)) * 3.2 - u_time * 2.4) * 0.012 * u_sub_bass * u_band;
      vec2 g = vec2(fbm(p.xz * 0.32), fbm(p.xz * 0.32 + 7.3)) - 0.5;
      n = normalize(vec3(g.x * 0.018 + rip, 1.0, g.y * 0.018 + rip));
      vec3 rr = reflect(rd, n);
      float fres = 0.04 + 0.96 * pow(1.0 - max(dot(-rd, n), 0.0), 5.0);
      vec3 racc; float rm; vec2 rid; float rsid; float rtr;
      float rt2 = march(p + n * 0.01, rr, 45.0, 64, racc, rm, rid, rsid, rtr);
      vec3 rc = racc;
      if (rt2 > 0.0){ vec3 rp = p + rr * rt2; rc += shade(rp, rr, rm, rid, rsid, normalAt(rp)) * exp(-0.03 * rt2) * rtr; }
      col = (shade(p, rd, mat, id, sid, n) + rc * (0.2 + 0.8 * fres) * 0.85) * trans;
    } else {
      col = shade(p, rd, mat, id, sid, n) * trans;
    }
  }
  vec3 fogCol = FOG * (0.7 + 0.6 * u_rms * u_band) + blackbody(0.35) * 0.004 * u_tension * u_band;
  col = mix(col, fogCol, fogAmt) + acc;
  col *= u_exposure;
  o = vec4(col, 1.0);
}`;

const FS_POST = `#version 300 es
precision highp float;
in vec2 v_uv; out vec4 o;
uniform sampler2D u_tex; uniform vec2 u_res; uniform float u_ca, u_frame, u_fade;
float h(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
vec3 aces(vec3 x){ return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
void main(){
  vec2 c = v_uv - 0.5;
  vec2 dir = c * u_ca;
  vec3 col = vec3(texture(u_tex, v_uv + dir).r, texture(u_tex, v_uv).g, texture(u_tex, v_uv - dir).b);
  float vig = smoothstep(1.05, 0.25, length(c * vec2(1.25, 1.0)));
  col *= mix(0.55, 1.0, vig);
  col = aces(max(col * 1.15 - 0.0015, 0.0));
  col = pow(col, vec3(1.0 / 2.2));
  col += (h(gl_FragCoord.xy + u_frame * 1.618) - 0.5) * (1.6 / 255.0);
  o = vec4(col * u_fade, 1.0);
}`;

// ─── Pure musical state ──────────────────────────────────────────────────────
function createState(score, telemetry) {
  const EV = score.events, meta = score.meta, SEC = score.sections, BARS = score.bars;
  const leads = EV.filter(e => e.inst === 'lead');
  for (let i = 0; i < leads.length; i++) leads[i].prevFret = i ? leads[i - 1].fret : leads[i].fret;
  const chordEv = EV.filter(e => e.inst === 'rhythm' || e.inst === 'organ' || e.inst === 'bass');
  const barAt = t => { let lo = 0, hi = BARS.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (BARS[m].t0 <= t) lo = m; else hi = m - 1; } return BARS[lo]; };
  const secIndex = t => { let k = 0; for (let i = 0; i < SEC.length; i++) if (t >= SEC[i].t0) k = i; return k; };
  const lowerBound = (arr, t) => { let lo = 0, hi = arr.length; while (lo < hi) { const m = (lo + hi) >> 1; if (arr[m].t < t) lo = m + 1; else hi = m; } return lo; };
  const climax = leads.find(e => e.role === 'climax' && e.bends.length >= 3);
  const T_WAVE = climax ? climax.bends[1].t0 + 0.35 : Infinity;
  const secT = id => SEC.find(s => s.id === id);
  const BREAKS = [[barT(35, 1.5), secT('solo').t0], [barT(51, 1.5), secT('final').t0]];
  function barT(b, p) { const B = BARS[b]; return B.t0 + (B.t1 - B.t0) * p / 12; }
  const inBreak = t => BREAKS.some(([a, b]) => t >= a && t < b);

  function centsAt(n, t) {
    let c = 0;
    for (const b of n.bends) { if (t < b.t0) break; const u = clamp((t - b.t0) / Math.max(1e-6, b.t1 - b.t0), 0, 1); c = b.from + (b.to - b.from) * ease(b.c, u); }
    const v = n.vib;
    if (v && t >= v.t) {
      const dep = v.d * (1 - Math.exp(-(t - v.t) / Math.max(0.005, v.k))), ph = 2 * Math.PI * v.r * (t - v.t);
      c += dep * 100 * (v.m === 'sym' ? 0.5 * Math.sin(ph) : 0.5 - 0.5 * Math.cos(ph));
    }
    return c;
  }
  function leadEnv(n, t) {
    const age = t - n.t; if (age < 0) return 0;
    const legato = n.art !== 'pick';
    const a = age < 0.012 ? age / 0.012 : 1;
    const sustain = Math.exp(-age / (legato ? 2.4 : 1.9)) * 0.75 + 0.25;
    const rel = age > n.dur ? Math.exp(-(age - n.dur) / 0.14) : 1;
    return n.vel * a * sustain * rel * (legato ? 0.8 : 1);
  }
  function activeLeads(t) {
    const out = [];
    let i = lowerBound(leads, t - 16);
    for (; i < leads.length && leads[i].t <= t; i++) {
      const n = leads[i], e = leadEnv(n, t);
      if (e > 0.004) out.push([e, n]);
    }
    out.sort((a, b) => b[0] - a[0]);
    return out.slice(0, 4);
  }

  // ── constant tables (integrations), 60 Hz ──
  const RATE = 60, NT = Math.ceil(meta.duration * RATE) + 2, dt = 1 / RATE;
  const tab = { hand: new Float32Array(NT), warm: new Float32Array(NT), motion: new Float32Array(NT), travel: new Float32Array(NT), band: new Float32Array(NT), act: new Float32Array(NT) };
  const TF = telemetry && telemetry.frames ? telemetry.frames : null;
  const tel = { rms: new Float32Array(NT), sub: new Float32Array(NT), lead: new Float32Array(NT), highs: new Float32Array(NT), att: new Float32Array(NT) };
  {
    let hand = 6, warm = 0, motion = 0, travel = 0, band = 0;
    let r = 0, s = 0, l = 0, h = 0, at = 0;
    const solo = secT('solo'), finalT = secT('final').t0;
    let soloNorm = 0;
    for (let pass = 0; pass < 2; pass++) {
      hand = 6; warm = 0; motion = 0; travel = 0; band = 0; r = s = l = h = at = 0;
      for (let i = 0; i < NT; i++) {
        const t = i * dt, al = activeLeads(t);
        let act = 0, fw = 0, fs = 0;
        for (const [e, n] of al) { act += e; fw += e; fs += e * n.fret; }
        act = Math.min(1, act);
        if (fw > 0.05) hand += (fs / fw - hand) * (1 - Math.exp(-dt / 1.6));
        warm += dt * act * 0.16 - dt * warm / 16;
        const B = barAt(t), sec = SEC[secIndex(t)].id;
        const bandTarget = t < BARS[1].t0 ? 0.2 : inBreak(t) ? 0 : t > score.meta.damp ? 0 : 1;
        band += (bandTarget - band) * (1 - Math.exp(-dt / (bandTarget > band ? 0.25 : 0.5)));
        const speed = (0.2 + 0.8 * Math.max(act, 0.5 * band)) * (inBreak(t) ? 0.03 : 1);
        motion += dt * speed;
        if (sec === 'solo') travel += dt * B.tension * (inBreak(t) ? 0 : 1) * (pass ? 1 / soloNorm : 1);
        if (TF) {
          const f = TF[Math.min(TF.length - 1, i)];
          r += (f.rms - r) * (1 - Math.exp(-dt / 0.25)); s += (f.sub_bass - s) * (1 - Math.exp(-dt / 0.3));
          l += (f.lead_presence - l) * (1 - Math.exp(-dt / 0.12)); h += (f.highs - h) * (1 - Math.exp(-dt / 0.15));
          at = Math.max(at * Math.exp(-dt / 0.09), f.attack_transient);
          tel.rms[i] = r; tel.sub[i] = s; tel.lead[i] = l; tel.highs[i] = h; tel.att[i] = at;
        }
        tab.hand[i] = hand; tab.warm[i] = warm; tab.motion[i] = motion; tab.travel[i] = travel; tab.band[i] = band; tab.act[i] = act;
        if (!pass && t < T_WAVE - 1.0 && t >= solo.t0) soloNorm = travel;
      }
      if (pass === 0 && soloNorm <= 0) soloNorm = 1;
    }
  }
  const sample = (arr, t) => { const x = clamp(t * RATE, 0, NT - 1.001), i = Math.floor(x), f = x - i; return arr[i] * (1 - f) + arr[i + 1] * f; };

  // ── camera rigs (all look from the nut end toward the bridge: -z) ──
  const RIG = {
    intro: (t, u, m, hz) => ({ p: [0.25, 0.62, 37.5 - 1.6 * u], q: [-0.4, 1.15, 24.0], fov: 38 }),
    verse1: (t, u, m, hz) => ({ p: [0.3 + 0.12 * Math.sin(m * 0.21), 2.35 + 0.05 * Math.sin(m * 0.13), hz + 6.4], q: [-0.1, 1.4, hz - 3.0], fov: 40 }),
    chorus1: (t, u, m, hz) => ({ p: [1.6 + 0.2 * Math.sin(m * 0.12), 3.3, hz + 10.0 - 1.2 * u], q: [-0.3, 1.05, hz - 5.0], fov: 46 }),
    verse2: (t, u, m, hz) => ({ p: [-0.35 - 0.12 * Math.sin(m * 0.2), 2.45, hz + 6.2], q: [0.15, 1.35, hz - 3.0], fov: 40 }),
    chorus2: (t, u, m, hz) => ({ p: [-3.2 - 0.2 * Math.sin(m * 0.1), 4.6 - 0.4 * u, hz + 12.0 - 1.5 * u], q: [0.3, 0.9, hz - 7.0], fov: 50 }),
    solo: (t, u, m, hz, tr) => { const z = 46 - 21.5 * clamp(tr, 0, 1.02); return { p: [0.1 * Math.sin(m * 0.17), 2.05 - 0.2 * clamp(tr, 0, 1), z], q: [0.0, 1.45, z - 8.5], fov: 44 + 8 * clamp(tr, 0, 1) }; },
    final: (t, u, m, hz) => ({ p: [0.6 * Math.sin(m * 0.05), 7.4 - 0.8 * u, 47.0 - 3 * u], q: [0.0, 0.6, 21.0], fov: 52 }),
    outro: (t, u, m, hz) => ({ p: [0.25, 0.62, 37.5], q: [-0.4, 1.15, 24.0], fov: 38 })
  };
  const BLEND = { intro: 0, verse1: 4, chorus1: 3, verse2: 3, chorus2: 3, solo: 0, final: 3.5, outro: -1 };

  function camera(t) {
    const k = secIndex(t), S = SEC[k], u = clamp((t - S.t0) / (S.t1 - S.t0), 0, 1);
    const m = sample(tab.motion, t), hz = zOfFret(sample(tab.hand, t)), tr = sample(tab.travel, t);
    let c = RIG[S.id](t, u, m, hz, tr);
    const bl = BLEND[S.id];
    if (k > 0 && bl !== 0) {
      const P = SEC[k - 1], dur = bl < 0 ? (S.t1 - S.t0) * 0.92 : bl;
      const w = smooth(0, 1, (t - S.t0) / dur);
      if (w < 1) {
        const pu = clamp((t - P.t0) / (P.t1 - P.t0), 0, 1);
        const pc = RIG[P.id](t, pu, m, hz, tr);
        c = { p: c.p.map((v, i) => mix(pc.p[i], v, w)), q: c.q.map((v, i) => mix(pc.q[i], v, w)), fov: mix(pc.fov, c.fov, w) };
      }
    }
    return c;
  }

  function pcLevels(t) {
    const L = new Array(12).fill(0);
    let i = lowerBound(chordEv, t - 8);
    for (; i < chordEv.length && chordEv[i].t <= t; i++) {
      const e = chordEv[i], age = t - e.t;
      if (e.inst === 'organ') {
        const a = clamp(age / 0.4, 0, 1) * (age > e.dur ? Math.exp(-(age - e.dur) / 0.5) : 1);
        for (const m of e.midis) L[m % 12] += e.vel * 0.55 * a;
      } else if (e.inst === 'bass') {
        const a = Math.min(1, age / 0.01) * Math.exp(-age / 1.1) * (age > e.dur ? Math.exp(-(age - e.dur) / 0.15) : 1);
        L[e.midi % 12] += e.vel * 0.7 * a;
      } else {
        const tau = e.kind === 'mute' ? 0.08 : e.kind === 'arp' ? 1.8 : 1.3;
        const a = Math.min(1, age / 0.015) * Math.exp(-age / tau);
        const ms = e.midis || [e.midi];
        for (const m of ms) L[m % 12] += e.vel * (e.midis ? 0.55 : 0.8) * a;
      }
    }
    return L.map(v => 1 - Math.exp(-v * 1.25));
  }

  function stateAt(t) {
    const S = SEC[secIndex(t)], B = barAt(t), fracBar = (t - B.t0) / (B.t1 - B.t0);
    const nb = BARS[Math.min(BARS.length - 1, B.i + 1)];
    const tension = mix(B.tension, nb.tension, smooth(0.6, 1, fracBar));
    const pressure = fracBar < 0.5 || B.pressure.length < 2 ? B.pressure[0] : B.pressure[1];
    const band = sample(tab.band, t), warm = sample(tab.warm, t);
    const soloU = S.id === 'solo' ? (t - S.t0) / (S.t1 - S.t0) : 0;
    let heat = 0.04 * tension, haze = 0, molten = 0;
    if (S.id === 'solo') { heat = mix(0.3, 1.0, soloU); haze = mix(0.15, 1.0, soloU) * (0.4 + 0.6 * band); molten = mix(0.08, 0.8, soloU); }
    if (S.id === 'final') { const u = (t - S.t0) / (S.t1 - S.t0); heat = mix(0.8, 0.35, u); haze = mix(0.6, 0.15, u); molten = mix(0.7, 0.3, u); }
    if (S.id === 'outro') { const u = (t - S.t0) / (S.t1 - S.t0); molten = mix(0.25, 0.0, u); heat = 0.1 * (1 - u); }
    const notes = activeLeads(t).map(([e, n]) => {
      const cents = centsAt(n, t);
      let fret = n.fret;
      if (n.art === 'slide') fret = mix(n.prevFret, n.fret, smooth(0, 1, (t - n.t) / 0.14));
      const zf = zOfFret(fret);
      const dir = n.str <= 3 ? -1 : 1;
      const age = t - n.t;
      return {
        str: n.str, zf, glow: e * (0.9 + 0.8 * n.vel) * (1 + 0.6 * Math.max(0, cents) / 200), defl: dir * (cents / 200) * SPACING,
        vib: 0.035 * n.vel * Math.exp(-age / 0.7) * (n.art === 'pick' ? 1 : 0.4), phase: age * 2 * Math.PI * (7 + 0.35 * (n.midi - 60)),
        width: 0.35 + Math.min(2.6, age * 1.4), vel: n.vel, id: n.id, onset: n.t, cents
      };
    });
    const pcs = pcLevels(t).map(v => v * (0.25 + 0.75 * band));
    // voice tube: first light, last light
    let key = Math.min(1, 0.12 + warm * 0.9) * (t > (leads[0] ? leads[0].t : 0) ? 1 : 0);
    key = Math.max(key * 0.85, 0) + 0.25 * sample(tab.act, t);
    if (t > meta.damp) key *= Math.exp(-(t - meta.damp) / 0.9);
    let spread = mix(0.1, 1.0, tension) * (0.3 + 0.7 * band);
    let wave = [0, 0, 0];
    const FT = secT('final').t0, OT = secT('outro').t0;
    if (t >= T_WAVE) {
      const r = (t - T_WAVE) * 15;
      const strength = t < FT ? 1.0 : t < OT ? mix(1.0, 0.45, smooth(FT, OT, t)) : mix(0.45, 0.2, smooth(OT, meta.damp, t));
      wave = [r, strength, 1];
      spread = Math.max(spread, t < OT ? 1.0 : 0.6);
    }
    const cool = t < OT ? 200 : mix(60, 0.5, smooth(OT, meta.damp - 0.6, t));
    const firstT = leads[0] ? leads[0].t : 1;
    let exposure = mix(0.55, 1.0, smooth(firstT - 1.0, firstT + 2.0, t));
    const fade = t < meta.damp + 1.0 ? 1 : 1 - smooth(meta.damp + 1.0, meta.duration - 0.25, t);
    const telI = x => sample(x, t);
    return {
      t, section: S.id, bar: B.i, field: Math.min(1, pcs.reduce((a, b) => a + b, 0) / 4 + (wave[2] ? wave[1] * 0.6 : 0) + key * 0.2), tension, pressure, band, warm, heat, haze, molten, spread, key, wave, cool, exposure, fade,
      notes, pcs, camera: camera(t),
      tel: TF ? { rms: telI(tel.rms), sub: telI(tel.sub), lead: telI(tel.lead), highs: telI(tel.highs), att: telI(tel.att) } : { rms: 0.5 * band, sub: 0.5 * band, lead: 0.5, highs: 0.3 * band, att: 0 }
    };
  }
  return { stateAt, leads, T_WAVE };
}

// ─── GL plumbing + the pure draw ─────────────────────────────────────────────
function create(canvas, score, telemetry, opts = {}) {
  const gl = canvas.getContext('webgl2', { antialias: false, preserveDrawingBuffer: !!opts.preserve, alpha: false, premultipliedAlpha: false, powerPreference: 'high-performance' });
  if (!gl) throw new Error('WebGL2 is required.');
  if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('EXT_color_buffer_float is required.');
  const compile = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const program = fs => {
    const p = gl.createProgram(); gl.attachShader(p, compile(gl.VERTEX_SHADER, VS)); gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
    gl.bindAttribLocation(p, 0, 'a'); gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const U = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i), name = info.name.replace(/\[0\]$/, ''); U[name] = gl.getUniformLocation(p, info.name); }
    return { p, U };
  };
  const scene = program(FS_SCENE), post = program(FS_POST);
  const vbo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  let W = 0, H = 0, tex = null, fbo = null;
  function resize(w, h) {
    if (w === W && h === H) return;
    W = w; H = h; canvas.width = w; canvas.height = h;
    if (tex) gl.deleteTexture(tex); if (fbo) gl.deleteFramebuffer(fbo);
    tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    fbo = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  resize(opts.width || 1920, opts.height || 1080);
  const ST = createState(score, telemetry);
  const n0 = new Float32Array(16), n1 = new Float32Array(16);

  // THE pure function: image = draw(gl, t)
  function draw(glCtx, t) {
    const s = ST.stateAt(t);
    const g = glCtx;
    g.bindVertexArray(vao);
    g.bindFramebuffer(g.FRAMEBUFFER, fbo); g.viewport(0, 0, W, H);
    g.useProgram(scene.p); const U = scene.U;
    g.uniform2f(U.u_res, W, H);
    g.uniform1f(U.u_time, t);
    g.uniform1f(U.u_rms, s.tel.rms); g.uniform1f(U.u_sub_bass, s.tel.sub); g.uniform1f(U.u_lead_transients, s.tel.lead);
    g.uniform1f(U.u_highs, s.tel.highs); g.uniform1f(U.u_attack_transient, s.tel.att);
    g.uniform3fv(U.u_camPos, s.camera.p); g.uniform3fv(U.u_camTgt, s.camera.q); g.uniform1f(U.u_fov, s.camera.fov);
    g.uniform1fv(U.u_pc, s.pcs);
    n0.fill(0); n1.fill(0);
    s.notes.forEach((n, i) => { n0.set([n.str, n.zf, n.glow, n.defl], i * 4); n1.set([n.vib, n.phase, n.width, n.vel], i * 4); });
    g.uniform4fv(U.u_n0, n0); g.uniform4fv(U.u_n1, n1);
    g.uniform1f(U.u_field, s.field); g.uniform1f(U.u_key, s.key); g.uniform1f(U.u_heat, s.heat); g.uniform1f(U.u_tension, s.tension); g.uniform1f(U.u_haze, s.haze);
    g.uniform1f(U.u_band, s.band); g.uniform1f(U.u_molten, s.molten); g.uniform1f(U.u_spread, s.spread); g.uniform1f(U.u_pressure, s.pressure);
    g.uniform1f(U.u_exposure, s.exposure); g.uniform3fv(U.u_wave, s.wave); g.uniform1f(U.u_cool, s.cool);
    g.drawArrays(g.TRIANGLES, 0, 3);
    g.bindFramebuffer(g.FRAMEBUFFER, null); g.viewport(0, 0, W, H);
    g.useProgram(post.p);
    g.activeTexture(g.TEXTURE0); g.bindTexture(g.TEXTURE_2D, tex); g.uniform1i(post.U.u_tex, 0);
    g.uniform2f(post.U.u_res, W, H);
    g.uniform1f(post.U.u_ca, 0.0012 + 0.011 * s.tel.att * (0.4 + 0.6 * s.band));
    g.uniform1f(post.U.u_frame, Math.round(t * 60) % 997);
    g.uniform1f(post.U.u_fade, s.fade);
    g.drawArrays(g.TRIANGLES, 0, 3);
    return s;
  }
  return { gl, draw: t => draw(gl, t), drawWith: draw, stateAt: ST.stateAt, resize, T_WAVE: ST.T_WAVE };
}

global.FilamentVisual = { create, zOfFret };
})(typeof window !== 'undefined' ? window : globalThis);
