"""Export small physical-velocity component spectra from Pencil snapshots.

Run on Vera; full snapshots stay there. Uses Pencil's reader and NumPy FFTs.
Example: python analysis/export_velocity_components.py runs/mixed-turbulence-kt
"""

import argparse
from pathlib import Path

import numpy as np
import pencil as pc


def physical_velocity(var, w):
    """Invert E=T00 and S=T0i for this nonmagnetic radiation-fluid run."""
    energy = np.asarray(var.rho, dtype=np.float64)
    momentum = np.asarray(var.uu, dtype=np.float64)
    radicand = (1 + w) ** 2 * energy**2 - 4 * w * np.sum(momentum**2, axis=0)
    if (not np.isfinite(energy).all() or not np.isfinite(momentum).all()
            or np.any(energy <= 0) or np.any(radicand < 0)):
        raise ValueError("Invalid conservative state in snapshot")
    rest_energy = (np.sqrt(radicand) - (1 - w) * energy) / (2 * w)
    velocity = momentum / (energy + w * rest_energy)
    if np.any(rest_energy <= 0) or np.any(np.sum(velocity**2, axis=0) >= 1):
        raise ValueError("Nonphysical fluid state in snapshot")
    return velocity


def component_spectra(velocity, lengths):
    """Return k, total, transverse, longitudinal power and Parseval error.

    Use unit-width spherical shells in fundamental-wavenumber units. Include
    all cube modes for Parseval checks; restrict exported plots to k < N/2.
    For k=0 put the mean-flow power in a separate mean column, not N or L.
    All powers include Pencil's 1/2 factor and are per shell (not per log k).
    """
    shape = velocity.shape[1:]  # z, y, x
    if len(set(shape)) != 1 or not np.allclose(lengths, lengths[0]):
        raise ValueError("This exporter is restricted to the present cubic runs")
    n = shape[0]
    modes = np.fft.fftfreq(n) * n
    kz, ky, kx = np.meshgrid(modes, modes, modes, indexing="ij")
    k2 = kx*kx + ky*ky + kz*kz
    shell = np.floor(np.sqrt(k2) + 0.5).astype(int)
    fourier = np.fft.fftn(velocity, axes=(1, 2, 3)) / np.prod(shape)
    dot = kx*fourier[0] + ky*fourier[1] + kz*fourier[2]
    coefficient = np.divide(dot, k2, out=np.zeros_like(dot), where=k2 > 0)
    longitudinal = np.stack([kx*coefficient, ky*coefficient, kz*coefficient])
    transverse = fourier - longitudinal
    transverse[:, 0, 0, 0] = 0
    total_mode = 0.5*np.sum(np.abs(fourier)**2, axis=0)
    long_mode = 0.5*np.sum(np.abs(longitudinal)**2, axis=0)
    trans_mode = 0.5*np.sum(np.abs(transverse)**2, axis=0)
    total = np.bincount(shell.ravel(), weights=total_mode.ravel())
    comp = np.bincount(shell.ravel(), weights=long_mode.ravel())
    vort = np.bincount(shell.ravel(), weights=trans_mode.ravel())
    mean = np.zeros_like(total)
    mean[0] = total_mode[0, 0, 0]
    np.testing.assert_allclose(total, vort+comp+mean, rtol=1e-10, atol=1e-16)
    real_power = 0.5*np.mean(np.sum(velocity**2, axis=0))
    parseval_error = abs(total.sum()-real_power)/max(real_power, 1e-30)
    if parseval_error > 1e-10:
        raise ValueError("FFT power failed Parseval consistency check")
    k = np.arange(len(total)) * 2*np.pi/lengths[0]
    return k, total, vort, comp, mean, parseval_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    data = run / "data"
    par = pc.read.param(datadir=str(data), quiet=True)
    for flag in ["lconservative", "lrelativistic", "ldensity_nolog", "lrelativistic_eos"]:
        if not getattr(par, flag, False):
            raise ValueError("This exporter requires " + flag + "=T")
    w = float(par.cs0)**2
    if not np.isclose(w, 1/3, rtol=1e-5):
        raise ValueError("Expected the radiation equation of state")
    names = sorted((p.name for p in (data / "proc0").glob("VAR*")
                    if p.name[3:].isdigit()), key=lambda name: int(name[3:]))
    if not names:
        raise FileNotFoundError("No numbered snapshots in " + str(data / "proc0"))
    # Pencil writes the final state to var.dat even when the stop time falls
    # between numbered snapshots. Include it unless its time duplicates VARn.
    if (data / 'proc0' / 'var.dat').is_file():
        names.append('var.dat')
    rows, summary = [], []
    for name in names:
        var = pc.read.var(var_file=name, datadir=str(data), trimall=True,
                          quiet=True, timing=False)
        if name=='var.dat' and summary and np.isclose(float(var.t),summary[-1][0],rtol=1e-12,atol=1e-12):
            continue
        velocity = physical_velocity(var, w)
        k, total, vort, comp, mean, error = component_spectra(velocity, par.lxyz)
        # Save only the same inscribed-shell range used by Pencil's power output.
        keep = np.arange(len(k)) < velocity.shape[-1]//2
        rows.append(np.column_stack([np.full(np.count_nonzero(keep), var.t),
                                     k[keep], total[keep], vort[keep], comp[keep], mean[keep]]))
        fluctuations = vort.sum()+comp.sum()
        summary.append([var.t, total.sum(), vort.sum(), comp.sum(), mean.sum(),
                        comp.sum()/max(fluctuations, 1e-30), error])
        print(f"{name}: t={float(var.t):.6g}, longitudinal fraction="
              f"{summary[-1][5]:.4f}, Parseval error={error:.2e}", flush=True)
    np.savetxt(data / "velocity_components.dat", np.vstack(rows), fmt="%.12e",
               header="t k total_shell vortical_shell compressional_shell mean_shell")
    np.savetxt(data / "velocity_component_summary.dat", summary, fmt="%.12e",
               header="t half_v2_all_modes vortical_all_modes compressional_all_modes "
                      "mean_power compressional_fraction parseval_relative_error")
    print("Wrote", data / "velocity_components.dat", flush=True)
    print("Wrote", data / "velocity_component_summary.dat", flush=True)


if __name__ == "__main__":
    main()
