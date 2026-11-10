"""Carrier-aided software tracking loops (PLL + DLL) for the built-in receiver.

Why this exists: ``l1_acquire.acquire_l1`` is an ACQUISITION device -- it
reports the correlation peak on the integer-SAMPLE grid, so its code-phase
noise is quantization, sigma = (chip_hz/fs)/sqrt(12) (~0.059 chips at
5 Msps, ~17 m of pseudorange). A real receiver's TRACKING front end drives
numerically controlled oscillators whose phase is continuous; the sub-sample
measurement is the loop's zero crossing, not a grid bin.

Structure mirrored here (all in software, on the same IQ files):

* Code NCO: continuous chip-phase state ``chi`` whose rate is FED FORWARD
  from the carrier loop (carrier aiding). The aiding sign depends on the
  frame (see Frame notes below): the NC/acquisition frame integrates
  dchi/dt = chip_hz*(1 - fd/carrier_hz); the coherent replica-anchor frame
  uses chip_hz*(1 + fd/carrier_hz); only residuals go through the (narrow)
  code loop.
* Analytic boundary-integral correlator: the local replica is the piecewise
  +-1 waveform code[floor(chi + offset + chip_hz*tau)], tau segment-local
  time. Its chip (and half-chip BOC) transitions fall at FRACTIONAL times
  (m - chi - offset)/chip_hz; the correlation integral is evaluated exactly
  by splitting the window at those crossings and using the segment's
  cumulative integral linearly interpolated at the fractional knots. c(.)
  is therefore continuous and monotone in chi -- no sample-grid staircase.
* DLL, default mode="el": CLASSIC non-coherent EARLY/LATE power
  discriminator D=(P_L-P_E)/(P_L+P_E). E and L are correlators on the
  acquisition-verified per-code-period FFT |corr|^2 surface, placed at the
  anchor-corrected predicted lag -+ ell/2 chips, so the discriminator
  zero coincides with the peak sitting on d_pred and chi books the delay
  at the window start (the tau_bar anchor correction is inherited).
  mode="nc": sub-sample parabolic PEAK fit of that same surface replaces
  the E/L ratio.
* mode="coh" (2026-11 rewrite): fully COHERENT early/late + Costas PLL.
  One nav-bit window of per-code-period product-sum correlations on the
  SAME sample-grid replica as acquisition, mirrored into the acquisition
  frame via base = -chi - drift*tau_bar (loop zero aperture-matched to
  acquisition and carrying the tau_bar anchor correction; E sits at
  base+ell/2, L at base-ell/2, i.e. mirrored vs the replica-lag frame).
  Each block's E/L/P is sign-aligned by its P value (data-bit robustness;
  straddling edge blocks collapse |P| and are dropped by a median gate)
  before the coherent sums; D = (|L|^2-|E|^2)/(|L|^2+|E|^2), slope-probe
  normalized like the el branch.
* PLL: second-order Costas loop on the sign-aligned per-block P phasors:
  within-window robust phase-slope fit feeds the frequency integrator
  (fd_fn is the feed-forward), cross-window lag-1 diffs cover single-block
  windows (E1), the +-0.45-cycle gate rejects nav-bit/secondary flips.
  The tracked NCO phase accumulates continuously in _phase_cyc (cycles)
  and is exported for carrier-phase observables; physically it follows
  -rho_carrier/lambda + per-SV constant (engine injects exactly that).
* E1 BOC(1,1): half-chip sign flips ride on the replica; the subcarrier is
  code-locked (flag ``boc_sub_code_locked``) -- flip to segment-locked to
  mimic acquire_l1's replica if ever needed.

chi follows the acquire_l1 convention exactly (same replica construction,
same segment-start alignment), so chi and code_phase_chips measure the same
physical quantity and are directly comparable on the trace grid.
"""
from __future__ import annotations

import numpy as np

from backend.synth import _lib
from backend.synth.engine import _glo_g1_code

_CODEGEN_ENUM = {"G": 0, "J": 1, "S": 2, "C": 3, "E": 6}

# coherent window = one navigation bit of the engine's NRZ modulation, ms
_T_COH_MS = {"G": 20, "J": 20, "S": 4, "E": 4, "C": 20, "R": 10}


def _code_table(sysc: str, prn: int, code_len: int) -> np.ndarray:
    if sysc == "R":
        return _glo_g1_code().astype(np.float64)
    sec_len = 25 if sysc == "E" else 0
    tab = _lib.code(_CODEGEN_ENUM[sysc], prn, code_len, sec_len)[0]
    return np.asarray(tab, dtype=np.float64)


class SVTracker:
    """One satellite's PLL + carrier-aided DLL over a shared IQ buffer.

    iq starts at the session origin (IQ-file sample 0 == trace t=0).
    fd0/chi0 seed the loops from a normal acquisition (same convention).
    """

    def __init__(self, get_window, fs: float, sysc: str, prn: int, *,
                 chip_hz: float, code_len: int, carrier_hz: float,
                 if_hz: float, fd0: float, chi0: float, boc: bool = False,
                 ell: float | None = None, pll_bw: float = 1.0,
                 dll_bw_hz: float = 0.5, t_coh_ms: float | None = None,
                 nc: bool = True, mode: str | None = None, fd_fn=None,
                 cn0_est: bool = False):
        """get_window(t0, ns) -> ns complex samples starting at absolute
        time t0 (a callable lets every SV of one band share cached IQ
        windows read from disk -- full runs are hundreds of MB).
        mode selects the code discriminator:
        * "el"  (default via callers): CLASSIC non-coherent EARLY/LATE
          power discriminator on the acquisition-verified per-block |corr|^2
          surface, E/L at +-ell/2 chips around the anchor-corrected
          predicted lag; skips the coherent PLL, uses fd_fn + FLL.
        * "nc": power-surface PEAK-TRACKING DLL (sub-sample parabolic
          peak fit instead of an E/L ratio).
        * "coh": coherent E/L DLL + second-order Costas PLL on sign-
          aligned per-block P phasors (carrier-phase observable from the
          continuously accumulated NCO phase).
        ``nc`` is kept for backward compatibility: nc=True maps to
        mode="nc", nc=False to mode="coh" when ``mode`` is not given.
        fd_fn(t)->Hz supplies carrier aiding (e.g. interpolated
        narrowed-acquisition Doppler on the trace grid)."""
        self._get = get_window
        self.fs = float(fs)
        self.sysc = sysc
        self.chip_hz = float(chip_hz)
        self.code_len = int(code_len)
        self.carrier_hz = float(carrier_hz)
        self.if_hz = float(if_hz)
        self.mode = mode or ("nc" if nc else "coh")
        if self.mode not in ("el", "nc", "coh"):
            raise ValueError(f"unknown tracker mode {mode!r}")
        # BOC(1,1) needs a tight E/L spacing: at ell=1 chip the E/L pair
        # straddles the +-0.5-chip BOC side lobes and an offset beyond
        # ~0.3 ch can slide the discriminator zero onto them (146 m false
        # lock); 0.5 chip keeps the capture region inside the main lobe.
        self.ell = float(ell) if ell is not None \
            else (0.5 if (self.mode in ("el", "coh") and boc) else 1.0)
        self.boc = bool(boc)
        self.code = _code_table(sysc, int(prn), self.code_len)
        if self.code.size < self.code_len:
            self.code = np.resize(self.code, self.code_len)
        # Frame notes (verified against the engine, run 20261106T084558776704):
        # the engine's mixer advances its code-grid argument g as
        # g(t) = -pr(t)*chip/C (physically correct), so the FILE code grid
        # drifts at +code_dop (= chip*fd/carrier) ch/s relative to a
        # zero-Doppler replica. acquire_l1 -- and this tracker's NC path,
        # which correlates through FFT lag (peak when the replica is
        # DELAYED by d, i.e. chi == c*d == -g mod L) -- live in the
        # acquisition frame, where the drift is -code_dop, hence the
        # chip*(1 - fd/carrier) aiding. The coherent path mirrors its
        # product-sum replica into the SAME acquisition frame
        # (base = -chi - drift*tau_bar), so every mode shares the frame,
        # the aiding sign and the tau_bar anchor correction.
        self._aid_sign = -1.0
        self.chi = float(chi0) % self.code_len       # chips, [0, L)
        self.fd = float(fd0)                          # Hz, rel. if_hz
        self._fd0 = float(fd0)                        # NCO base freq (pass-1)
        self.phase = 0.0                              # carrier NCO phase [rad]
        self.t_coh = float(t_coh_ms or _T_COH_MS.get(sysc, 20)) / 1e3
        self._npp = max(int(round(self.fs * self.code_len / self.chip_hz)), 4)
        self.nc = self.mode in ("nc", "el")          # legacy flag
        self._el_gain: float | None = None           # D/chip slope (el/coh)
        self._fd_fn = fd_fn
        # coherent-mode PLL state: second-order Costas loop. fd_fn gives the
        # feed-forward; _pll_off is the frequency-integrator residual [Hz];
        # _phase_cyc is the CONTINUOUS tracked NCO phase in cycles (the
        # carrier-phase observable, never wrapped). Loop gains from
        # pll_bw (zeta fixed at 0.7, updates once per DLL window).
        self._pll_off = 0.0
        self._phase_cyc = 0.0
        self._pt = 0.0                                  # booked-through t [s]
        self._chi_rate = 0.0                            # chips/s for log interp
        wn = 2.0 * np.pi * float(pll_bw)
        self._pll_kp = 0.5                                   # phase prop.
        self._pll_ki = float(np.clip(2.0 * 0.7 * wn * self.t_coh,
                                     0.005, 0.35))           # freq integr.
        if self.mode == "coh" and self.t_coh <= 0.005:
            # Single-block coherent windows (E1: t_coh=4 ms < 10 ms code
            # period): the loop moves only on ONE cross-window lag-1
            # difference, so a wide-bandwidth ki just makes the frequency
            # integrator twitch between DLL windows and leaks into phase.
            # A/B 2026-11-09: E phRMS 0.0252 -> 0.0199 cyc at ki=0.01,
            # error_m unchanged; 0.005 shrinks jitter more but slows
            # pull-in (error_m 0.39 -> 0.54 at track_s=2). Cap at 0.01.
            self._pll_ki = min(self._pll_ki, 0.01)
        self._lastP: tuple[complex, float] | None = None     # (P, t_abs)
        self._p_ref = 0.0
        self.n_dropped = 0
        self.n_pll_skipped = 0
        self._sp: np.ndarray | None = None
        self._fll_off = 0.0
        self._loc: np.ndarray | None = None
        self._search_samples = max(int(round(3.0 * self.fs / self.chip_hz)), 4)
        self._dll_bw = float(dll_bw_hz)
        # Negative-feedback sign: FIXED +1 by convention for all modes.
        # el/nc: D is defined as (peak - predicted)/ratio form. coh: the
        # mirrored-base coherent D = (|L|^2-|E|^2)/(|L|^2+|E|^2) has NEGATIVE
        # slope at the main correlation peak (replica late -> E stronger ->
        # D < 0 -> chi falls), so chi += 2*pi*Bw*T*D is negative feedback.
        # DO NOT probe it: on BOC(1,1) the first-update probes can land in
        # the POSITIVE-slope inter-peak region between the equal-height
        # +-0.5-chip side lobes and invert the loop (observed: E6 locked
        # 0.30 ch below the true peak with the |P| surface unambiguously
        # showing the peak 0.30 ch up).
        self._k_sign = 1.0
        self.t_log: list[float] = []
        self.chi_log: list[float] = []
        self.fd_log: list[float] = []
        self.phase_log: list[float] = []
        self.p_log: list[complex] = []
        self.e_log: list[float] = []
        # Optional C/N0 moment estimator (OFF by default so existing
        # regressions stay byte-identical). Per code-period block we
        # collect |corr| samples -- the envelope of a complex Gaussian +
        # tone, i.e. Rician / non-central chi with 2 dof -- bucketed by
        # the SECOND the block starts in. cn0_dbhz(sec) then solves the
        # Kay-1980 moment relation r = (y^2+4y+2)/(y+1)^2, r = M4/M2^2,
        # y = A^2/(2 sigma_c^2) = SNR over one integration period
        # T = npp/fs, giving C/N0 = 10*log10(y/T) dB-Hz.
        self._cn0_acc: dict[int, list] | None = {} if cn0_est else None

    # ---- C/N0 moment estimator -------------------------------------------------
    def _cn0_push(self, mags: np.ndarray, t0: float) -> None:
        """Accumulate per-block |corr| moments into 1-s buckets keyed by
        floor(block start). Safe to call from every discriminator branch
        (coh: |P| of kept blocks; el/nc: |corr| at the fitted lag)."""
        if self._cn0_acc is None or mags.size == 0:
            return
        c = self._npp / self.fs                       # block period [s]
        starts = t0 + np.arange(mags.size) * c
        secs = np.floor(starts).astype(int)
        for sec, v in zip(secs.tolist(), mags.tolist()):
            acc = self._cn0_acc.get(sec)
            if acc is None:
                acc = self._cn0_acc[sec] = [0, 0.0, 0.0]
            acc[0] += 1
            acc[1] += v * v
            acc[2] += v ** 4

    def cn0_dbhz(self, sec: int, min_blocks: int = 30) -> float | None:
        """C/N0 [dB-Hz] estimated from the blocks that started in second
        ``sec`` (call with sec = epoch-1 for a lag-aligned 1 Hz report).
        Returns None when the bucket is empty/thin or the moment ratio is
        out of the solvable range (r must lie in (1, 2) for a Rician
        envelope; noise-only buckets sit at r->2, saturated at r->1)."""
        acc = None if self._cn0_acc is None else self._cn0_acc.get(sec)
        if acc is None or acc[0] < min_blocks:
            return None
        n = acc[0]
        m2 = acc[1] / n
        m4 = acc[2] / n
        if m2 <= 0.0:
            return None
        r = m4 / (m2 * m2)
        if not (1.0 < r < 2.0):
            return None
        # (r-1) y^2 + (2r-4) y + (r-2) = 0; positive root in closed form
        # (discriminant = 4(2-r)): y = (2-r+sqrt(2-r)) / (r-1).
        s = np.sqrt(2.0 - r)
        y = float((s * s + s) / (r - 1.0))
        y = min(max(y, 1e-9), 1e9)
        return float(10.0 * np.log10(y / (self._npp / self.fs)))

    # ---- signal / replica helpers -------------------------------------------
    def _derot_window(self, t0: float, T: float):
        n0 = int(round(t0 * self.fs))
        ns = int(round(T * self.fs))
        seg = self._get(t0, ns)
        tt = np.arange(ns) / self.fs                     # segment-local [s]
        theta = self.phase + 2.0 * np.pi * self.fd * tt
        dseg = seg * np.exp(-1j * (2.0 * np.pi * self.if_hz * (t0 + tt)
                                   + theta))
        return dseg, ns

    # ---- loop updates ---------------------------------------------------------
    def _block_replicas(self, nb: int, npp: int, base0: float, half: float):
        """Per-block E/L/P sample-grid replicas over the coherent window,
        mirrored into the acquisition frame: the replica at window-sample i
        is code[floor(base + (chip_hz/fs) i)] with base = base0 (+0.5*ell
        for E, base0 for P, base0 - 0.5*ell for L -- mirrored, so E is the
        LESS-delayed side, matching the el branch's D sign convention).
        Identical floor-grid construction as the verified acquisition
        replica (incl. BOC(1,1) code-locked half-chip flips), so the loop
        zero is aperture-matched to acquisition."""
        c = self.chip_hz / self.fs
        idx = np.arange(nb * npp, dtype=np.float64)
        pbase = base0 + c * idx
        out = []
        for off in (+half, 0.0, -half):
            p = pbase + off
            if self.boc:
                mh = np.floor(2.0 * p).astype(np.int64)
                vals = self.code[np.mod(mh >> 1, self.code_len)] \
                    * np.where(mh & 1, -1.0, 1.0)
            else:
                vals = self.code[np.mod(np.floor(p).astype(np.int64),
                                        self.code_len)]
            out.append(vals.reshape(nb, npp))
        return out

    def _pll_coh_step(self, pal: np.ndarray, tk: np.ndarray, t0: float) -> None:
        """Second-order Costas PLL step from the SIGN-ALIGNED per-block P
        phasors of one coherent window. Costas target: aligned P real and
        positive, so the phase residual is wrap(arg P) at the window start
        and the frequency residual is the robust slope of the block phases
        within the window (+-0.45-cycle diff gate rejects any surviving
        bit-flip pair). Single-block windows (E1 4 ms) fall back to the
        cross-window lag-1 diff, gated the same way and coasted on a flip.
        NOTE: must NOT be called from discriminator probes."""
        f_res: float | None = None
        phi_res = 0.0
        if len(pal) >= 2:
            th = np.angle(pal)
            # Lag-L diffs (L up to 5 blocks) instead of lag-1: at 1 ms the
            # per-block phase noise (~0.26 cyc on this interference-limited
            # IQ) makes a lag-1 slope a 100+-Hz-noise random walk that the
            # loop can never settle; lag-5 keeps |ambiguity| < +-100 Hz
            # (seed is within +-25) and averages the noise ~sqrt(5) wider
            # than the +-25 Hz pull-in bound.
            L = min(5, len(pal) - 1)
            i0 = np.arange(len(pal) - L)
            Tb = float(tk[1] - tk[0])
            d = (np.angle(pal[i0 + L] * np.conj(pal[i0])) + np.pi) \
                % (2.0 * np.pi) - np.pi
            ok = np.abs(d) < 0.45 * 2.0 * np.pi
            if int(np.count_nonzero(ok)) >= max(1, len(d) // 2):
                f_res = float(np.median(d[ok])) / (2.0 * np.pi * L * Tb)
                w = (th - 2.0 * np.pi * f_res * tk + np.pi) % (2.0 * np.pi) \
                    - np.pi
                phi_res = float(np.mean(w)) / (2.0 * np.pi)
        elif len(pal) == 1 and self._lastP is not None \
                and abs(pal[0]) >= 0.5 * self._p_ref:
            # single-block window (E1): cross-window lag-1 diff, but ONLY
            # for clean windows -- a nav-bit-straddling block has a
            # collapsed, phase-distorted P that would random-walk the
            # frequency integrator (observed E-side phase resid ~1 cycle).
            z = pal[0] * np.conj(self._lastP[0])
            e = float(np.arctan2(z.imag, z.real)) / (2.0 * np.pi)
            dt = max(t0 + float(tk[0]) - self._lastP[1], 1e-6)
            if abs(e) < 0.45:
                f_res = e / dt
            else:
                self.n_pll_skipped += 1                 # nav-bit flip: coast
        if f_res is not None and abs(f_res) < 300.0:
            self._pll_off = float(np.clip(self._pll_off + self._pll_ki * f_res,
                                          -250.0, 250.0))
        if phi_res:
            self.phase += 2.0 * np.pi * self._pll_kp * phi_res
            self._phase_cyc += self._pll_kp * phi_res
        if len(pal) and (len(pal) >= 2 or abs(pal[0]) >= 0.5 * self._p_ref):
            self._lastP = (complex(pal[-1]), t0 + float(tk[-1]))

    def _advance_coh_phase(self, t_end: float) -> None:
        """Book the coherent NCO state up to absolute time t_end (the
        oscillator does not stop even when the window is dropped / the loop
        coasts). Bookkeeping uses the ABSOLUTE time, not a nominal T: the
        log branch in run() samples between window boundaries and reads the
        phase back at rate fd via _phase_at(), which keeps the recorded
        phase continuous at the SAMPLE time. (Fixed-T booking made the log
        alternate by fd*(log_offset into window) ~ 12 cyc at 50 ms logs /
        20 ms windows -- a pure sampling artifact in phase_rms.)"""
        dt = t_end - self._pt
        self.phase += 2.0 * np.pi * self.fd * dt
        self._phase_cyc += self.fd * dt
        self._pt = t_end

    def _chi_at(self, t: float) -> float:
        """Code phase at time t: linear back/forward from the booked state
        at self._pt (same sampling-artifact fix as _phase_at)."""
        return (self.chi + self._chi_rate * (t - self._pt)) % self.code_len

    def _phase_at(self, t: float) -> float:
        return self._phase_cyc + self.fd * (t - self._pt)

    def _raw_disc(self, t0: float, T: float,
                  probe: bool = False) -> tuple[float, complex]:
        """Discriminator. Modes:
        * mode="el": CLASSIC non-coherent EARLY/LATE power discriminator --
          E and L correlators sample the same per-block |corr|^2 surface at
          the anchor-corrected predicted lag -+ ell/2 chips; the block sums
          at the fitted lag still feed the FLL / power metric.
        * mode="nc": the VERIFIED acquisition surface -- per code
          period block |corr|^{2} (same FFT recipe and replica convention
          as acquire_l1), summed over blocks into acc[lag]. The loop error
          is (sub-lag peak - predicted lag), parabolic-interpolated, i.e.
          a peak-tracking DLL that removes the integer-sample quantization
          while inheriting acquisition's interference robustness.
          Returns D = (peak - chi) in chips, stable with chi += K*D.
        * mode="coh": COHERENT E/L on sign-aligned per-code-period blocks
          (see class docstring); D = (|L|^2-|E|^2)/(|L|^2+|E|^2) with the
          acquisition-frame mirrored base -chi - drift*tau_bar + offset,
          so the zero inherits the tau_bar anchor correction; the aligned
          P phasors drive the Costas PLL (skipped when probe=True).
        probe=True: state-free evaluation for slope/sign probing."""
        dseg, ns = self._derot_window(t0, T)
        if self.mode in ("nc", "el"):
            npp, L = self._npp, self.code_len
            nb = max(ns // npp, 1)
            loc = self._get_loc()                      # cached conj-FFT replica
            x = dseg[:nb * npp].reshape(nb, npp)
            cors = [np.fft.ifft(np.fft.fft(x[k]) * loc) for k in range(nb)]
            acc = np.zeros(npp)
            for cr in cors:
                acc += np.abs(cr) ** 2
            c = self.chip_hz / self.fs                 # chips per sample
            # Anchor correction: acc averages the per-block correlation
            # PEAKS, i.e. the signal delay at the MEAN block centre
            # t0+tau_bar, while chi is booked as the phase at t0 (run()
            # logs it at the update boundary). Locking d_pred to the
            # window-start chi would force a steady-state bias
            # drift*tau_bar, with drift = aid_sign*chip*fd/carrier the
            # delay drift of the tracked grid (=-code_dop in acq frame).
            # That term is exactly the measured -6.1e-6 ch/Hz Doppler
            # proportional error (chip/carrier * 9.47 ms = 6.15e-6).
            # Predict the lag at the mean block centre instead, so lock
            # implies chi == delay at t0.
            tau_bar = 0.5 * nb * (npp / self.fs)
            drift = self._aid_sign * self.chip_hz * self.fd / self.carrier_hz
            d_pred = ((self.chi + drift * tau_bar) / c) % npp
            i0 = int(round(d_pred))
            w = self._search_samples
            idx = (np.arange(i0 - w, i0 + w + 1)) % npp
            seg = acc[idx]
            j = int(np.argmax(seg))
            if j == 0 or j == len(idx) - 1:            # no clean local max
                if self.mode == "nc":
                    return 0.0, 0j
                jf, delta = i0 % npp, 0.0      # el: still discriminate at d_pred
            else:
                a, b, cc = seg[j - 1], seg[j], seg[j + 1]
                denom = a - 2.0 * b + cc
                delta = 0.0 if denom == 0 else 0.5 * (a - cc) / denom
                delta = float(np.clip(delta, -1.0, 1.0))
                jf = int(idx[j])
            if self.mode == "nc":
                d_fit = (jf + delta) % npp             # fitted lag [samples]
                err = (d_fit - d_pred + npp / 2) % npp - npp / 2
                D = err * c
            else:                                      # "el"
                D = self._el_disc(acc, d_pred, npp)
            # complex block sums at the fitted lag -> FLL input + power metric
            jj = int(round(jf + delta)) % npp
            sp = np.array([cors[k][jj] for k in range(nb)])
            self._sp = sp
            if not probe:
                self._cn0_push(np.abs(sp), t0)
            # power metric: INCOHERENT sum. |mean(sp)| would collapse under
            # the nav-bit signs riding on the blocks (the coherent sum
            # cancels), which mis-arms the drop rule; per-block |sp| is the
            # stable lock-strength measure.
            return D, complex(float(np.sum(np.abs(sp))))
        # ---- coherent branch (mode == "coh") --------------------------------
        npp = self._npp
        nb = max(ns // npp, 1)
        tau_bar = 0.5 * nb * (npp / self.fs)
        drift = self._aid_sign * self.chip_hz * self.fd / self.carrier_hz
        base0 = -self.chi - drift * tau_bar              # chips, acq frame
        bE, bP, bL = self._block_replicas(nb, npp, base0, 0.5 * self.ell)
        x = dseg[:nb * npp].reshape(nb, npp)
        e_k = (x * bE).sum(1)
        p_k = (x * bP).sum(1)
        l_k = (x * bL).sum(1)
        mag = np.abs(p_k)
        keep = mag > 0.5 * float(np.median(mag))   # nav-bit edge blocks
        # collapse |P| (half +half destructively) -> drop them, like the
        # legacy straddling-window drop rule but per block.
        if not keep.any():
            return 0.0, 0j
        if not probe:
            self._cn0_push(mag[keep], t0)
        # Per-block data-bit sign, decided by P against the last aligned
        # phasor (Costas 180 deg decision; the E/L blocks share the same
        # bit sign). The chain CONTINUES across windows from the previous
        # window's last aligned block (self._lastP) -- otherwise a
        # single-block window (E1) would force +1 and every data flip
        # would look like a 0.5-cycle PLL jump (observed: half the PLL
        # updates coasted, the E frequency integrator froze, and the code
        # error sat at 4e-4*Delta-fd chips). Also carries through blocks
        # dropped by the median gate (ref is not reset there).
        s = np.ones(nb)
        ref: complex | None = None if self._lastP is None \
            else complex(self._lastP[0])
        for k in range(nb):
            if not keep[k]:
                continue
            if ref is not None and float((p_k[k] * np.conj(ref)).real) < 0.0:
                s[k] = -1.0
            ref = s[k] * p_k[k]
        P = complex(np.sum(s * keep * p_k))
        E = complex(np.sum(s * keep * e_k))
        Lc = complex(np.sum(s * keep * l_k))
        e2, l2 = abs(E) ** 2, abs(Lc) ** 2
        D = (l2 - e2) / (l2 + e2 + 1e-30)
        if not probe:
            ki = np.flatnonzero(keep)
            tk = ki.astype(np.float64) * (npp / self.fs)
            self._pll_coh_step((s * p_k)[keep], tk, t0)
        return D, P

    def _el_disc(self, acc: np.ndarray, d_pred: float, npp: int) -> float:
        """Classic non-coherent EARLY/LATE power discriminator. The E and L
        correlators sample the per-block power surface at the anchor-
        corrected predicted lag -+ ell/2 chips (fractional-sample offsets
        by linear interp of the wrapped surface); D = (P_L - P_E)/(P_L + P_E)
        is zero exactly when the correlation peak is CENTERED on d_pred --
        so the E/L pair inherits the tau_bar anchor correction of the peak
        branch for free (the loop locks with the delay booked at t0, not at
        the mean block centre). Same sign convention as the nc branch's
        err (peak later than predicted -> D > 0), so the loop keeps its
        built-in k_sign = +1 negative feedback. Raw D is dimensionless;
        _dll_update divides by the probed slope so dll_bw_hz keeps the
        loop-bandwidth meaning it has in the nc branch."""
        half = 0.5 * self.ell * npp / self.code_len    # ell/2 chips [samples]

        def pow_at(lag: float) -> float:
            # 3-point PARABOLIC interp (same recipe as the peak fit), NOT
            # linear: |R|^2 has a kink at the peak and at 5 Msps the E/L
            # pair straddles it by only ~1-2 samples -- linear interp then
            # mis-reads the two sides asymmetrically and shifts the
            # discriminator zero a random ~0.01-0.02 ch per SV.
            li = lag % npp
            j = int(round(li))
            dl = li - j                               # in [-0.5, 0.5]
            a, b, cc = acc[(j - 1) % npp], acc[j % npp], acc[(j + 1) % npp]
            v = (a * 0.5 * dl * (dl - 1.0) + b * (1.0 - dl * dl)
                 + cc * 0.5 * dl * (dl + 1.0))
            return max(v, 0.0)

        pe = pow_at(d_pred - half)                     # replica less delayed
        pl = pow_at(d_pred + half)
        return (pl - pe) / (pl + pe + 1e-30)

    def _probe_el_gain(self, t0: float) -> None:
        """|D|/chip slope near lock: the raw E-L ratio has a signal-shape
        dependent gain (~2-3 /chip at ell=1), so normalize D to chip units
        (the nc branch's D already is in chips). Probing +-0.15 ch keeps
        both probes inside the linear region of the +-ell/2 S-curve."""
        q = 0.15
        chi0 = self.chi
        self.chi = (chi0 + q) % self.code_len
        dp, _ = self._raw_disc(t0, self.t_coh, probe=True)
        self.chi = (chi0 - q) % self.code_len
        dm, _ = self._raw_disc(t0, self.t_coh, probe=True)
        self.chi = chi0
        # dD/dchi is NEGATIVE for this convention (chi late -> L side
        # weaker), so normalize with |slope|; the loop's k_sign=+1 keeps
        # negative feedback (chi below the zero sees D > 0 and is pulled up).
        s = abs(dp - dm) / (2.0 * q)
        self._el_gain = s if s > 0.2 else 1.0

    def _get_loc(self) -> np.ndarray:
        """conj(fft(local)) with local = replica over one code period,
        identical construction to acquire_l1 (incl. E1 BOC subcarrier)."""
        if getattr(self, "_loc", None) is None:
            t = np.arange(self._npp) / self.fs
            idx = np.floor(t * self.chip_hz).astype(int) % self.code_len
            local = self.code[idx].astype(np.float64)
            if self.boc:
                sub = np.where(np.floor(2.0 * t * self.chip_hz).astype(np.int64)
                               & 1, -1.0, 1.0)
                local = local * sub
            self._loc = np.conj(np.fft.fft(local))
        return self._loc

    def _fll_update(self) -> None:
        """NC mode carrier refinement: P-block phases rotate at (fd_true-fd)
        cycles per block; leaky-integrate the median of lag-L diffs into
        _fll_off so the aiding term converges to within a few Hz of truth.
        Lag L=10 keeps diffs unambiguous (|resid| < 1/(2L·Tblk) = 50 Hz)
        once fd_fn seeded +-25 Hz; bit-flip pairs land near +-0.5 cycles
        and are gated out."""
        sp = self._sp
        nb = len(sp)
        if nb < 3:
            return
        L = min(10, nb - 1)
        mag = np.abs(sp)
        thr = 0.5 * float(np.median(mag))
        diffs = []
        for k in range(nb - L):
            if mag[k] > thr and mag[k + L] > thr:
                z = sp[k + L] * np.conj(sp[k])
                c = np.arctan2(z.imag, z.real) / (2.0 * np.pi)
                if abs(c) < 0.4:
                    diffs.append(c)
        if len(diffs) >= 3:
            err = float(np.median(diffs)) / (L * self._npp / self.fs)
            self._fll_off += 0.1 * err

    def _wrap_chip(self, x: float) -> float:
        L = self.code_len
        return ((x + L / 2.0) % L) - L / 2.0

    def _dll_update(self, t0: float) -> complex:
        T = self.t_coh
        chi_b = self.chi
        fdot = 0.0
        if self._fd_fn is not None:
            # carrier aid: FLL residual (nc/el) or PLL frequency integrator
            # (coh) on top of the feed-forward Doppler
            off = self._fll_off if self.mode in ("nc", "el") else self._pll_off
            self.fd = float(self._fd_fn(t0)) + off
            # Acceleration feedforward. The aiding is a CONSTANT-VELOCITY
            # code model; a first-order DLL under a Doppler-RATE signal
            # (geo+clock drift ~0.1-0.2 Hz/s on this run) converges to a
            # steady-state ramp error e = (chip*fdot/carrier)/(2*pi*B_eff)
            # -- measured +0.018 ch on G23/G31 while fd swept. Feed the
            # second derivative through the aiding integral: the loop must
            # advance chi by the true position increment over T, i.e.
            # chip*(1 + aid*fd/carrier)*T + chip*aid*fdot*T^2/(2*carrier).
            h = 0.5
            fdot = (float(self._fd_fn(t0 + h))
                    - float(self._fd_fn(t0 - h))) / (2.0 * h)
        elif self.mode == "coh":
            # NO aiding grid (receiver self-aided cold start): the second-
            # order loop must still close -- let the PLL frequency
            # integrator drive the NCO exactly as (fd_fn + off) does above,
            # so the 300 s Doppler ramp (~0.1-0.2 Hz/s here, >30 Hz total)
            # is tracked instead of freezing the oscillator at fd0.
            self.fd = self._fd0 + self._pll_off
        aid_t = self.chip_hz * (1.0 + self._aid_sign
                                * self.fd / self.carrier_hz) * T \
            + 0.5 * self.chip_hz * self._aid_sign * fdot * T * T \
            / self.carrier_hz
        if self.mode in ("el", "coh") and self._el_gain is None:
            self._probe_el_gain(t0)                    # once, seeds the norm
        D, cP = self._raw_disc(t0, T)
        if self.mode in ("el", "coh"):
            D = D / self._el_gain                      # chip units, like nc
        if self._fd_fn is not None and self.mode in ("nc", "el"):
            self._fll_update()
        if abs(cP) < (0.15 if self.mode == "coh" else 0.25) * self._p_ref:
            self.n_dropped += 1                         # interference: coast
            self.chi += aid_t
            self.chi %= self.code_len
            if self.mode == "coh":
                self._advance_coh_phase(t0 + T)         # books _pt, NCO runs
            else:
                self._pt = t0 + T
            self._chi_rate = self._wrap_chip(self.chi - chi_b) / T
            return cP
        self.chi += aid_t \
            + self._k_sign * 2.0 * np.pi * self._dll_bw_hz() * T * D
        self.chi %= self.code_len
        if self.mode == "coh":
            self._advance_coh_phase(t0 + T)             # books _pt
        else:
            self._pt = t0 + T
        self._chi_rate = self._wrap_chip(self.chi - chi_b) / T
        self._p_ref = max(0.995 * self._p_ref, abs(cP))
        return cP

    def _dll_bw_hz(self) -> float:
        return getattr(self, "_dll_bw", 0.5)

    # ---- session driver ----------------------------------------------------------
    def run(self, *, t_end: float, log_period_s: float = 1.0,
            dll_bw_hz: float | None = None):
        if dll_bw_hz is not None:
            self._dll_bw = float(dll_bw_hz)
        if abs(log_period_s * 1000 - round(log_period_s * 1000)) > 1e-6:
            raise ValueError("log_period_s must be a multiple of 1 ms")
        next_dll = next_log = 0.0
        t = 0.0
        eps = 1e-9
        while t < t_end - eps:
            if t >= next_log - eps:
                # Sample AT the log time: the loop books chi/phase to the
                # window END before the log branch runs, so reading the raw
                # state alternates by rate*(window offset) -- e.g. a 12-cycle
                # square wave in phase_log at 50 ms logs / 20 ms windows.
                self.t_log.append(next_log)
                self.chi_log.append(self._chi_at(next_log))
                self.fd_log.append(self.fd)
                self.phase_log.append(self._phase_at(next_log))
                self.p_log.append(getattr(self, "_p_last", 0j))
                next_log += log_period_s
            if t >= next_dll - eps:                      # DLL first: its
                self._p_last = self._dll_update(t)       # window hosts the P
                next_dll += self.t_coh                   # and the coherent
            nxt = min(next_dll, next_log)                # PLL step (coh)
            t = nxt if nxt > t else t + 1e-4

    def measure(self, t_k: float) -> dict:
        """Snapshot on the trace grid point nearest t_k (acquisition frame).
        coh mode additionally reports the continuous tracked carrier phase
        (cycles) and the PLL frequency-integrator residual [Hz]."""
        if not self.t_log:
            return {}
        k = min(range(len(self.t_log)), key=lambda i: abs(self.t_log[i] - t_k))
        p = abs(self.p_log[k])
        out = {"t_s": self.t_log[k], "chi_chips": self.chi_log[k],
               "doppler_hz": self.fd_log[k], "p_abs": p}
        if self.mode == "coh" and self.phase_log:
            out["carrier_phase_cycles"] = self.phase_log[k]
            out["pll_off_hz"] = self._pll_off
            out["n_pll_skipped"] = self.n_pll_skipped
        return out
