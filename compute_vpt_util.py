import numpy as np
LORENZ_LYAP = 0.9056
LORENZ_DT = 0.02
def compute_vpt(true_traj, pred_traj, threshold=0.4, dt=LORENZ_DT, lyap=LORENZ_LYAP):
    sigma = np.sqrt(np.mean(np.sum(true_traj**2, axis=1)))
    errors = np.sqrt(np.sum((pred_traj - true_traj)**2, axis=1)) / sigma
    exceed = np.where(errors > threshold)[0]
    n_steps = len(true_traj) if len(exceed) == 0 else exceed[0]
    return n_steps * dt * lyap, n_steps, errors
