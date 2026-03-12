'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function HeroOrbit() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const hero = canvas.parentElement as HTMLElement;
    const W = () => hero.clientWidth;
    const H = () => hero.clientHeight;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W(), H());
    renderer.setClearColor(0x050505, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(57, W() / H(), 0.1, 200);
    camera.position.set(0, 2.6, 9.4);
    camera.lookAt(0, -0.35, 0);

    const clock = new THREE.Clock();
    let T = 0;
    let cycleT = 0;
    const CYCLE = 20;

    // Math utils
    const eo3 = (x: number) => 1 - Math.pow(1 - x, 3);
    const ei3 = (x: number) => x * x * x;
    const eio = (x: number) => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
    const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
    const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
    const map = (x: number, a: number, b: number, c: number, d: number) => lerp(c, d, clamp((x - a) / (b - a), 0, 1));
    const rand = (a = 0, b = 1) => a + Math.random() * (b - a);

    // Orbital ellipse
    const OA = 4.1, OB = 2.45, OTILT = Math.PI / 5.6;
    function orbitPos(a: number) {
      const x = OA * Math.cos(a), zF = OB * Math.sin(a);
      return new THREE.Vector3(x, zF * Math.sin(OTILT), zF * Math.cos(OTILT));
    }
    function orbitTan(a: number) {
      const dx = -OA * Math.sin(a), dzF = OB * Math.cos(a);
      return new THREE.Vector3(dx, dzF * Math.sin(OTILT), dzF * Math.cos(OTILT)).normalize();
    }

    // Ring
    const ringPts: THREE.Vector3[] = [];
    for (let i = 0; i <= 300; i++) ringPts.push(orbitPos((i / 300) * Math.PI * 2));
    const ringCurve = new THREE.CatmullRomCurve3(ringPts, true);
    const orbitRing = new THREE.Mesh(
      new THREE.TubeGeometry(ringCurve, 400, 0.020, 8, true),
      new THREE.MeshBasicMaterial({ color: 0xFF2020 })
    );
    orbitRing.position.y = -0.7;
    scene.add(orbitRing);

    const glowRings: Array<[number, number, number]> = [[0.055, 0.20, 0xFF2020], [0.12, 0.07, 0xFF2020], [0.22, 0.025, 0xFF2020], [0.38, 0.008, 0xFF4040]];
    glowRings.forEach(([r, op, col]) => {
      const m = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false });
      const glow = new THREE.Mesh(new THREE.TubeGeometry(ringCurve, 200, r, 6, true), m);
      glow.position.y = -0.7;
      scene.add(glow);
    });

    const arrowPos = orbitPos(Math.PI * 0.12);
    const arrowTan = orbitTan(Math.PI * 0.12);
    const arrowMesh = new THREE.Mesh(
      new THREE.ConeGeometry(0.072, 0.16, 6),
      new THREE.MeshBasicMaterial({ color: 0xFF2020, transparent: true, opacity: 0.9 })
    );
    arrowMesh.position.copy(arrowPos);
    arrowMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), arrowTan);
    scene.add(arrowMesh);

    [-0.3, -0.18, -0.06].forEach(off => {
      const dp = orbitPos(Math.PI * 0.12 + off);
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.04, 8, 8),
        new THREE.MeshBasicMaterial({ color: 0xFF2020, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      dot.position.copy(dp);
      scene.add(dot);
    });

    // Core
    const coreGroup = new THREE.Group();
    coreGroup.position.y = -0.7;
    scene.add(coreGroup);
    coreGroup.add(new THREE.Mesh(
      new THREE.SphereGeometry(0.36, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x120000 })
    ));

    const coreGlows: Array<{ mesh: THREE.Mesh; base: number }> = [];
    const coreGlowDefs: Array<[number, number]> = [[0.52, 0.22], [0.80, 0.08], [1.30, 0.025], [2.0, 0.008]];
    coreGlowDefs.forEach(([r, op]) => {
      const m = new THREE.Mesh(
        new THREE.SphereGeometry(r, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xFF2020, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide })
      );
      coreGroup.add(m);
      coreGlows.push({ mesh: m, base: op });
    });

    type SpinningRing = THREE.Mesh<THREE.TorusGeometry, THREE.MeshBasicMaterial> & { _spd: number };
    const coreRings: SpinningRing[] = [];
    const coreRingDefs: Array<[number, number, number]> = [[0.58, 0.36, 0.8], [0.76, 0.42, -0.52], [0.94, 0.25, 0.3]];
    coreRingDefs.forEach(([r, rx, spd]) => {
      const mesh = new THREE.Mesh(
        new THREE.TorusGeometry(r, 0.007, 6, 64),
        new THREE.MeshBasicMaterial({ color: 0xFF2020, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false })
      );
      const m = Object.assign(mesh, { _spd: spd }) as SpinningRing;
      m.rotation.x = rx;
      coreGroup.add(m);
      coreRings.push(m);
    });

    const coreLight = new THREE.PointLight(0xFF2020, 2.5, 12);
    scene.add(coreLight);
    scene.add(new THREE.AmbientLight(0x1a0000, 0.5));

    // PDF document builder
    function buildDocMesh(lineColor = 0xFF2020) {
      const g = new THREE.Group() as THREE.Group & { _halo: THREE.Mesh; _haloMat: THREE.MeshBasicMaterial };
      const W2 = 0.70, H2 = 0.92, C = 0.18;
      const bodyShape = new THREE.Shape();
      bodyShape.moveTo(-W2 / 2, -H2 / 2);
      bodyShape.lineTo(-W2 / 2, H2 / 2);
      bodyShape.lineTo(W2 / 2 - C, H2 / 2);
      bodyShape.lineTo(W2 / 2, H2 / 2 - C);
      bodyShape.lineTo(W2 / 2, -H2 / 2);
      bodyShape.closePath();
      g.add(new THREE.Mesh(new THREE.ShapeGeometry(bodyShape), new THREE.MeshBasicMaterial({ color: 0x080808 })));

      const bord = [[-W2 / 2, -H2 / 2], [-W2 / 2, H2 / 2], [W2 / 2 - C, H2 / 2], [W2 / 2, H2 / 2 - C], [W2 / 2, -H2 / 2], [-W2 / 2, -H2 / 2]]
        .map(([x, y]) => new THREE.Vector3(x, y, 0.002));
      g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(bord), new THREE.LineBasicMaterial({ color: lineColor })));

      const foldShape = new THREE.Shape();
      foldShape.moveTo(W2 / 2 - C, H2 / 2);
      foldShape.lineTo(W2 / 2, H2 / 2 - C);
      foldShape.lineTo(W2 / 2 - C, H2 / 2 - C);
      foldShape.closePath();
      g.add(new THREE.Mesh(new THREE.ShapeGeometry(foldShape), new THREE.MeshBasicMaterial({ color: lineColor, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false })));

      const lMat = new THREE.LineBasicMaterial({ color: lineColor, transparent: true, opacity: 0.22 });
      [-0.30, -0.08, 0.14, 0.34].forEach(y => {
        const w2 = y === 0.34 ? 0.12 : W2 / 2 - 0.11;
        g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-W2 / 2 + 0.1, y, 0.003), new THREE.Vector3(w2, y, 0.003)]), lMat));
      });

      const GS = 0.12;
      const haloShape = new THREE.Shape();
      haloShape.moveTo(-W2 / 2 - GS, -H2 / 2 - GS);
      haloShape.lineTo(-W2 / 2 - GS, H2 / 2 + GS);
      haloShape.lineTo(W2 / 2 - C, H2 / 2 + GS);
      haloShape.lineTo(W2 / 2 + GS, H2 / 2 - C);
      haloShape.lineTo(W2 / 2 + GS, -H2 / 2 - GS);
      haloShape.closePath();

      const haloMat = new THREE.MeshBasicMaterial({ color: lineColor, transparent: true, opacity: 0.06, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
      const halo = new THREE.Mesh(new THREE.ShapeGeometry(haloShape), haloMat);
      halo.position.z = -0.02;
      g.add(halo);
      g._halo = halo;
      g._haloMat = haloMat;
      return g;
    }

    const docIn = buildDocMesh(0xFF2020);
    const docOut = buildDocMesh(0xFF8020);
    docIn.visible = false;
    docOut.visible = false;
    scene.add(docIn);
    scene.add(docOut);

    // Scanner
    const scanGroup = new THREE.Group();
    scene.add(scanGroup);
    const scanLineMat = new THREE.MeshBasicMaterial({ color: 0x60FFFF, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const scanGlowMat = new THREE.MeshBasicMaterial({ color: 0x20CCCC, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const scanLine = new THREE.Mesh(new THREE.PlaneGeometry(0.76, 0.038), scanLineMat);
    const scanGlow = new THREE.Mesh(new THREE.PlaneGeometry(0.76, 0.24), scanGlowMat);
    scanGroup.add(scanLine);
    scanGroup.add(scanGlow);

    // Shockwave
    const shockMat = new THREE.MeshBasicMaterial({ color: 0xFF2020, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, wireframe: true });
    const shockMesh = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.02, 4, 32), shockMat);
    scene.add(shockMesh);
    let shockT = -1;

    // Particles
    const MAX_P = 400;
    const pPositions = new Float32Array(MAX_P * 3);
    const pVelocities = new Float32Array(MAX_P * 3);
    const pLife = new Float32Array(MAX_P);
    const pMaxLife = new Float32Array(MAX_P);
    const pCyan = new Uint8Array(MAX_P);
    const pColors = new Float32Array(MAX_P * 3);
    const pGeom = new THREE.BufferGeometry();
    pGeom.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
    pGeom.setAttribute('color', new THREE.BufferAttribute(pColors, 3));
    const pMat = new THREE.PointsMaterial({ size: 0.04, vertexColors: true, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true });
    const particles = new THREE.Points(pGeom, pMat);
    scene.add(particles);
    let pHead = 0;

    function emit(pos: THREE.Vector3, vel: THREE.Vector3, life: number, redness: number, orangeness: number, cyanness: number) {
      const i = pHead % MAX_P;
      pHead++;
      pPositions[i * 3] = pos.x;
      pPositions[i * 3 + 1] = pos.y;
      pPositions[i * 3 + 2] = pos.z;
      pVelocities[i * 3] = vel.x;
      pVelocities[i * 3 + 1] = vel.y;
      pVelocities[i * 3 + 2] = vel.z;
      pLife[i] = life;
      pMaxLife[i] = life;
      pCyan[i] = cyanness > 0.5 ? 1 : 0;
      const r = cyanness > 0.5 ? 0.2 : redness;
      const gC = cyanness > 0.5 ? 0.9 : orangeness * 0.4;
      const b = cyanness > 0.5 ? 0.9 : 0;
      pColors[i * 3] = r;
      pColors[i * 3 + 1] = gC;
      pColors[i * 3 + 2] = b;
    }

    function stepParticles(dt: number) {
      for (let i = 0; i < MAX_P; i++) {
        if (pLife[i] <= 0) continue;
        pLife[i] -= dt;
        if (pLife[i] <= 0) { pPositions[i * 3 + 1] = -999; continue; }
        pPositions[i * 3] += pVelocities[i * 3] * dt;
        pPositions[i * 3 + 1] += pVelocities[i * 3 + 1] * dt;
        pPositions[i * 3 + 2] += pVelocities[i * 3 + 2] * dt;
        pVelocities[i * 3 + 1] -= 1.2 * dt;
        const a = pLife[i] / pMaxLife[i];
        pColors[i * 3] *= 0.98 + 0.02 * a;
      }
      pGeom.attributes.position.needsUpdate = true;
      pGeom.attributes.color.needsUpdate = true;
    }

    // HUD & UI helpers
    function setHud(mask: number) {
      for (let i = 0; i < 5; i++) {
        const el = document.getElementById('h' + i);
        if (el) el.classList.toggle('show', Boolean((mask >> i) & 1));
      }
    }

    function showCtr(pct: number) {
      const ctr = document.getElementById('hero-counter');
      const num = document.getElementById('ctr-num');
      const content = document.querySelector('.hero-content') as HTMLElement | null;
      if (ctr) ctr.classList.add('show');
      if (num) num.textContent = Math.round(pct) + '%';
      if (content) content.style.opacity = '0';
    }

    function hideCtr() {
      const ctr = document.getElementById('hero-counter');
      const content = document.querySelector('.hero-content') as HTMLElement | null;
      if (ctr) ctr.classList.remove('show');
      if (content) content.style.opacity = '1';
    }

    function showChip(id: string) {
      const el = document.getElementById(id);
      if (el) el.classList.add('show');
    }

    function hideChip(id: string) {
      const el = document.getElementById(id);
      if (el) el.classList.remove('show');
    }

    let docAngle = Math.PI;
    let lastTrailT = 0;
    let burstFired = false;
    let animId: number;

    function animate() {
      animId = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      T += dt;
      cycleT = (cycleT + dt / CYCLE) % 1;
      const c = cycleT;

      // Animate core
      coreRings.forEach(r => { r.rotation.z += r._spd * dt; });
      coreGlows.forEach(g => { (g.mesh.material as THREE.MeshBasicMaterial).opacity = g.base * (0.7 + 0.3 * Math.sin(T * 2.3)); });
      coreLight.intensity = 2.5 + 0.8 * Math.sin(T * 1.8);

      // Shockwave
      if (shockT >= 0) {
        shockT += dt;
        const sp = shockT * 2.5;
        shockMesh.scale.setScalar(sp);
        shockMesh.rotation.y = T * 2;
        shockMat.opacity = Math.max(0, 0.5 - shockT);
        if (shockT > 1) shockT = -1;
      }

      // Phase logic
      if (c < 0.10) {
        const p = c / 0.10;
        docIn.visible = true; docOut.visible = false;
        scanLineMat.opacity = 0; scanGlowMat.opacity = 0;
        hideCtr(); setHud(0);
        if (p < 0.45) {
          const fly = eo3(p / 0.45);
          const target = orbitPos(Math.PI);
          docIn.position.lerpVectors(new THREE.Vector3(-10, 0.6, 0), target, fly);
          docIn.lookAt(camera.position);
          docIn.rotateZ(lerp(0.35, 0, fly));
          docAngle = Math.PI;
          if (p > 0.08) showChip('chip-in');
        } else {
          docAngle = Math.PI;
          docIn.position.copy(orbitPos(docAngle));
          docIn.lookAt(camera.position);
        }
        burstFired = false; hideChip('chip-out');

      } else if (c < 0.56) {
        const p = (c - 0.10) / (0.56 - 0.10);
        docIn.visible = true; docOut.visible = false;
        scanLineMat.opacity = 0; scanGlowMat.opacity = 0; hideCtr();
        const speed = lerp(1.5, 5.2, clamp(p * 1.6, 0, 1));
        docAngle += dt * speed;
        const pos = orbitPos(docAngle);
        docIn.position.copy(pos); docIn.lookAt(camera.position);
        const banking = Math.sin(docAngle + Math.PI * 0.5) * lerp(0.04, 0.14, p);
        docIn.rotateZ(banking);
        docIn._haloMat.opacity = lerp(0.06, 0.18, p) * (0.7 + 0.3 * Math.sin(T * 6));
        const trailFreq = lerp(0.07, 0.020, p);
        if (T - lastTrailT > trailFreq) {
          lastTrailT = T;
          const vel = new THREE.Vector3(rand(-0.5, 0.5), rand(-0.5, 0.5), rand(-0.3, 0.3));
          vel.multiplyScalar(lerp(0.4, 2.0, p));
          emit(pos, vel, lerp(0.35, 1.1, p), 1.0, p * 0.22, 0.0);
        }
        const hudMask = ((1 << Math.min(Math.floor(p * 7), 5)) - 1) & 0x1F;
        setHud(hudMask);

      } else if (c < 0.72) {
        const p = (c - 0.56) / (0.72 - 0.56);
        docAngle += dt * 5.2;
        const pos = orbitPos(docAngle);
        showCtr(p * 100); setHud(0x1F);
        if (p < 0.55) {
          docIn.visible = true; docOut.visible = false;
          const scanP = p / 0.55;
          const scanY = lerp(-0.43, 0.43, eio(scanP));
          scanGroup.position.copy(pos); scanGroup.quaternion.copy(docIn.quaternion);
          scanLine.position.y = scanY; scanGlow.position.y = scanY;
          const scanAmp = Math.sin(scanP * Math.PI);
          scanLineMat.opacity = 0.95 * scanAmp; scanGlowMat.opacity = 0.30 * scanAmp;
          docIn.position.copy(pos); docIn.lookAt(camera.position);
          if (Math.random() > 0.55) {
            const sp = pos.clone().add(new THREE.Vector3(rand(-0.35, 0.35), scanY, rand(-0.05, 0.05)));
            emit(sp, new THREE.Vector3(rand(-0.5, 0.5), rand(0.3, 1.2), rand(-0.3, 0.3)), rand(0.3, 0.7), 0.2, 0.9, 1.0);
          }
          if (Math.random() > 0.7) {
            const ep = pos.clone().add(new THREE.Vector3(rand(-0.4, 0.4), rand(-0.5, 0.5), 0));
            emit(ep, new THREE.Vector3(rand(-1, 1), rand(-1, 1), rand(-0.5, 0.5)), 0.4, 1.0, 0.1, 0.0);
          }
        } else {
          scanLineMat.opacity = 0; scanGlowMat.opacity = 0;
          if (!burstFired) {
            burstFired = true; shockT = 0; shockMesh.position.copy(pos);
            for (let i = 0; i < 80; i++) {
              const vel = new THREE.Vector3(rand(-1, 1), rand(-1, 1), rand(-1, 1)).normalize().multiplyScalar(rand(2.5, 7));
              const isCyan = Math.random() > 0.55;
              emit(pos.clone(), vel, rand(0.5, 1.4), isCyan ? 0.2 : 1.0, isCyan ? 0.85 : rand(0, 0.35), isCyan ? 1.0 : 0.0);
            }
            coreLight.intensity = 12;
          }
          docIn.visible = false; docOut.visible = true;
          docOut.position.copy(pos); docOut.lookAt(camera.position);
          docOut._haloMat.opacity = 0.15;
          coreLight.intensity = lerp(8, 2.5, map(p, 0.55, 0.72, 0, 1));
        }

      } else if (c < 0.88) {
        const p = (c - 0.72) / (0.88 - 0.72);
        docIn.visible = false; docOut.visible = true;
        scanLineMat.opacity = 0; scanGlowMat.opacity = 0;
        hideCtr(); hideChip('chip-in'); setHud(0);
        if (p < 0.52) {
          docAngle += dt * 3.2;
          const pos = orbitPos(docAngle);
          docOut.position.copy(pos); docOut.lookAt(camera.position);
          docOut.rotateZ(Math.sin(docAngle + Math.PI * 0.5) * 0.08);
          docOut._haloMat.opacity = 0.12 * (0.7 + 0.3 * Math.sin(T * 5));
          if (T - lastTrailT > 0.032) {
            lastTrailT = T;
            const vel = new THREE.Vector3(rand(-0.6, 0.6), rand(-0.6, 0.6), rand(-0.3, 0.3));
            emit(pos, vel, 0.55, 1.0, 0.5, 0.0);
          }
          showChip('chip-out');
        } else {
          const esc = ei3((p - 0.52) / 0.48);
          const launchP = orbitPos(docAngle);
          const dest = new THREE.Vector3(11, 3.5, -2.5);
          docOut.position.lerpVectors(launchP, dest, esc);
          docOut.lookAt(camera.position);
          docOut.rotateZ(esc * 0.55);
          docOut._haloMat.opacity = lerp(0.12, 0, esc);
          if (esc > 0.4) hideChip('chip-out');
        }
      } else {
        docIn.visible = false; docOut.visible = false;
        scanLineMat.opacity = 0; scanGlowMat.opacity = 0;
        hideCtr(); hideChip('chip-in'); hideChip('chip-out'); setHud(0);
        burstFired = false; docAngle = Math.PI;
        docIn._haloMat.opacity = 0.06; docOut._haloMat.opacity = 0.06;
      }

      stepParticles(dt);
      renderer.render(scene, camera);
    }

    animate();

    const handleResize = () => {
      camera.aspect = W() / H();
      camera.updateProjectionMatrix();
      renderer.setSize(W(), H());
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      scene.clear();
    };
  }, []);

  return <canvas id="orbit-canvas" ref={canvasRef} />;
}