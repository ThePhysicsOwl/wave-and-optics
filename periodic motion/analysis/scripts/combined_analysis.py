import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

# Set high-quality plotting style defaults
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#718096'
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['xtick.color'] = '#4A5568'
plt.rcParams['ytick.color'] = '#4A5568'
plt.rcParams['text.color'] = '#2D3748'
plt.rcParams['axes.labelcolor'] = '#2D3748'
plt.rcParams['axes.titlecolor'] = '#1A202C'

# Curated harmonious color palette
COLORS = {
    'displacement': '#2B6CB0',  # Royal/Slate Blue
    'velocity': '#2F855A',      # Emerald Green
    'acceleration': '#C53030',  # Crimson Red
    'potential': '#805AD5',     # Royal Purple
    'kinetic': '#DD6B20',       # Dark Orange
    'total_energy': '#2D3748',  # Charcoal Grey
    'amplitude': '#6B46C1',     # Dark Purple
    'omega': '#319795',         # Teal
    'freq': '#2F855A',          # Forest Green
    'period': '#DD6B20',        # Dark Orange
    'grid': '#E2E8F0'
}

# Exponential decay envelope model
def exp_decay(t_val, A, B, C):
    return A * np.exp(-B * t_val) + C

def fit_envelope(t, y, label, distance=50):
    """
    Fits exponential decay envelopes (upper and lower) to oscillation data.
    Uses two-stage peak detection (peaks of the peaks) to trace the beats.
    """
    # 1. Find all peaks of y
    peaks_idx, _ = find_peaks(y, distance=distance)
    t_peaks = t[peaks_idx]
    y_peaks = y[peaks_idx]
    
    # Find beat maxima of y (peaks of the peaks)
    beat_max_idx, _ = find_peaks(y_peaks, distance=10)
    t_beat_max = t_peaks[beat_max_idx]
    y_beat_max = y_peaks[beat_max_idx]
    
    # 2. Find all troughs of y
    troughs_idx, _ = find_peaks(-y, distance=distance)
    t_troughs = t[troughs_idx]
    y_troughs = y[troughs_idx]
    
    # Find beat minima of y (troughs of the troughs)
    beat_min_idx, _ = find_peaks(-y_troughs, distance=10)
    t_beat_min = t_troughs[beat_min_idx]
    y_beat_min = y_troughs[beat_min_idx]
    
    # Fits bounds: [A, B, C]
    p0_guess = [0.4 * np.max(y), 0.003, 0.65 * np.max(y)]
    bounds_val = ([0, 0, 0], [2 * np.max(y), 1, 2 * np.max(y)])
    
    # Fit upper envelope
    try:
        popt_peaks, _ = curve_fit(exp_decay, t_beat_max, y_beat_max, p0=p0_guess, bounds=bounds_val)
        upper_envelope = exp_decay(t, *popt_peaks)
    except Exception as e:
        print(f"Warning: {label} upper envelope fit failed: {e}")
        upper_envelope = None
        
    # Fit lower envelope
    try:
        popt_troughs, _ = curve_fit(exp_decay, t_beat_min, -y_beat_min, p0=p0_guess, bounds=bounds_val)
        lower_envelope = -exp_decay(t, *popt_troughs)
    except Exception as e:
        print(f"Warning: {label} lower envelope fit failed: {e}")
        lower_envelope = None
        
    return upper_envelope, lower_envelope

def main():
    # Load the datasets
    print("Loading datasets...")
    df_theta = pd.read_csv("data/t_vs_theta.csv")
    df_v = pd.read_csv("data/t_vs_v.csv")
    df_accel = pd.read_csv("data/t_vs_accel.csv")
    df_tau = pd.read_csv("data/t_vs_tau.csv")
    df_U = pd.read_csv("data/t_vs_U.csv")
    df_K = pd.read_csv("data/t_vs_K.csv")
    df_E = pd.read_csv("data/t_vs_E.csv")
    df_T = pd.read_csv("data/t_vs_T.csv")
    df_freq = pd.read_csv("data/t_vs_freq.csv")
    df_omega = pd.read_csv("data/t_vs_omega.csv")
    df_amplitude = pd.read_csv("data/t_vs_amplitude.csv")
    
    t = df_theta["t"].values
    theta = df_theta["theta"].values
    v = df_v["v"].values
    accel = df_accel["accel"].values
    tau = df_tau["tau"].values
    U = df_U["U"].values
    K = df_K["K"].values
    E = df_E["E"].values
    T = df_T["T"].values
    freq = df_freq["freq"].values
    omega = df_omega["omega"].values
    amplitude = df_amplitude["amplitude"].values
    
    # Fit envelopes for all quantities
    print("Fitting envelopes...")
    theta_upper, theta_lower = fit_envelope(t, theta, "Displacement", distance=50)
    v_upper, v_lower = fit_envelope(t, v, "Velocity", distance=50)
    accel_upper, accel_lower = fit_envelope(t, accel, "Acceleration", distance=50)
    tau_upper, tau_lower = fit_envelope(t, tau, "Torque", distance=50)
    U_upper, U_lower = fit_envelope(t, U, "Potential Energy", distance=25)
    K_upper, K_lower = fit_envelope(t, K, "Kinetic Energy", distance=25)
    E_upper, E_lower = fit_envelope(t, E, "Total Energy", distance=25)
    
    # 1. KINEMATICS COMBINED GRAPH
    # Save three versions of kinematics combined plots: 300s, 600s, 2000s
    for t_max in [300, 600, 2000]:
        print(f"Generating combined kinematics plot for t_max = {t_max}s...")
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Style all axes consistently
        for ax in axes.flat:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#718096')
            ax.spines['bottom'].set_color('#718096')
            ax.grid(True, linestyle='--', alpha=0.5, color=COLORS['grid'])
        
        # Displacement Plot (Top-Left)
        axes[0, 0].plot(t, theta, color=COLORS['displacement'], linewidth=1.2, label='Displacement')
        if theta_upper is not None:
            axes[0, 0].plot(t, theta_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Upper Envelope')
        if theta_lower is not None:
            axes[0, 0].plot(t, theta_lower, color='#E53E3E', linestyle='--', linewidth=1.5, label='Lower Envelope')
        axes[0, 0].set_title('Displacement vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes[0, 0].set_xlabel('Time (s)', fontsize=10)
        axes[0, 0].set_ylabel(r'Displacement $\theta$ (rad)', fontsize=10)
        axes[0, 0].set_xlim(0, t_max)
        axes[0, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Velocity Plot (Top-Right)
        axes[0, 1].plot(t, v, color=COLORS['velocity'], linewidth=1.2, label='Velocity')
        if v_upper is not None:
            axes[0, 1].plot(t, v_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Upper Envelope')
        if v_lower is not None:
            axes[0, 1].plot(t, v_lower, color='#E53E3E', linestyle='--', linewidth=1.5, label='Lower Envelope')
        axes[0, 1].set_title('Velocity vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes[0, 1].set_xlabel('Time (s)', fontsize=10)
        axes[0, 1].set_ylabel(r'Velocity $v$ (rad/s)', fontsize=10)
        axes[0, 1].set_xlim(0, t_max)
        axes[0, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Acceleration Plot (Bottom-Left)
        axes[1, 0].plot(t, accel, color=COLORS['acceleration'], linewidth=1.2, label='Acceleration')
        if accel_upper is not None:
            axes[1, 0].plot(t, accel_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Upper Envelope')
        if accel_lower is not None:
            axes[1, 0].plot(t, accel_lower, color='#E53E3E', linestyle='--', linewidth=1.5, label='Lower Envelope')
        axes[1, 0].set_title('Acceleration vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes[1, 0].set_xlabel('Time (s)', fontsize=10)
        axes[1, 0].set_ylabel(r'Acceleration $a$ (rad/s$^2$)', fontsize=10)
        axes[1, 0].set_xlim(0, t_max)
        axes[1, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Superimposed Plot (Bottom-Right)
        axes[1, 1].plot(t, theta, color=COLORS['displacement'], linewidth=1.5, label=r'Displacement $\theta$ (rad)')
        axes[1, 1].plot(t, v, color=COLORS['velocity'], linewidth=1.5, label=r'Velocity $v$ (rad/s)')
        axes[1, 1].plot(t, accel, color=COLORS['acceleration'], linewidth=1.5, label=r'Acceleration $a$ (rad/s$^2$)')
        axes[1, 1].set_title('Superimposed Kinematics', fontsize=12, fontweight='bold', pad=10)
        axes[1, 1].set_xlabel('Time (s)', fontsize=10)
        axes[1, 1].set_ylabel('Amplitude (scaled units)', fontsize=10)
        axes[1, 1].set_xlim(0, t_max)
        axes[1, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        fig.suptitle(f'Harmonic Oscillator Kinematics Analysis (t = 0 to {t_max}s)', fontsize=15, fontweight='bold', y=0.98)
        
        filename = f"kinematics_combined_0_{t_max}.png"
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved {filename}")

    # 2. ENERGY COMBINED GRAPH
    # Save three versions of energy combined plots: 75s, 600s, 2000s
    for t_max in [75, 600, 2000]:
        print(f"Generating combined energy plot for t_max = {t_max}s...")
        fig_en, axes_en = plt.subplots(2, 2, figsize=(15, 10))
        
        # Style all axes consistently
        for ax in axes_en.flat:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#718096')
            ax.spines['bottom'].set_color('#718096')
            ax.grid(True, linestyle='--', alpha=0.5, color=COLORS['grid'])
        
        # Potential Energy Plot (Top-Left)
        axes_en[0, 0].plot(t, U, color=COLORS['potential'], linewidth=1.2, label='Potential Energy $U$')
        if U_upper is not None:
            axes_en[0, 0].plot(t, U_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Upper Envelope')
        if U_lower is not None:
            axes_en[0, 0].plot(t, U_lower, color='#E53E3E', linestyle='--', linewidth=1.5, label='Lower Envelope')
        axes_en[0, 0].set_title('Potential Energy vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_en[0, 0].set_xlabel('Time (s)', fontsize=10)
        axes_en[0, 0].set_ylabel('Energy $U$ (J)', fontsize=10)
        axes_en[0, 0].set_xlim(0, t_max)
        axes_en[0, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Kinetic Energy Plot (Top-Right)
        axes_en[0, 1].plot(t, K, color=COLORS['kinetic'], linewidth=1.2, label='Kinetic Energy $K$')
        if K_upper is not None:
            axes_en[0, 1].plot(t, K_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Upper Envelope')
        if K_lower is not None:
            axes_en[0, 1].plot(t, K_lower, color='#E53E3E', linestyle='--', linewidth=1.5, label='Lower Envelope')
        axes_en[0, 1].set_title('Kinetic Energy vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_en[0, 1].set_xlabel('Time (s)', fontsize=10)
        axes_en[0, 1].set_ylabel('Energy $K$ (J)', fontsize=10)
        axes_en[0, 1].set_xlim(0, t_max)
        axes_en[0, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Total Energy Plot (Bottom-Left)
        axes_en[1, 0].plot(t, E, color=COLORS['total_energy'], linewidth=1.2, label='Total Energy $E$')
        if E_upper is not None:
            axes_en[1, 0].plot(t, E_upper, color='#E53E3E', linestyle='--', linewidth=1.5, label='Decay Trendline')
        axes_en[1, 0].set_title('Total Energy vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_en[1, 0].set_xlabel('Time (s)', fontsize=10)
        axes_en[1, 0].set_ylabel('Energy $E$ (J)', fontsize=10)
        axes_en[1, 0].set_xlim(0, t_max)
        axes_en[1, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Superimposed Energy Plot (Bottom-Right)
        axes_en[1, 1].plot(t, U, color=COLORS['potential'], linewidth=1.5, label='Potential $U$')
        axes_en[1, 1].plot(t, K, color=COLORS['kinetic'], linewidth=1.5, label='Kinetic $K$')
        axes_en[1, 1].plot(t, E, color=COLORS['total_energy'], linewidth=1.8, label='Total $E$')
        axes_en[1, 1].set_title('Superimposed Energy', fontsize=12, fontweight='bold', pad=10)
        axes_en[1, 1].set_xlabel('Time (s)', fontsize=10)
        axes_en[1, 1].set_ylabel('Energy (J)', fontsize=10)
        axes_en[1, 1].set_xlim(0, t_max)
        axes_en[1, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        fig_en.suptitle(f'Harmonic Oscillator Energy Analysis (t = 0 to {t_max}s)', fontsize=15, fontweight='bold', y=0.98)
        
        filename_en = f"energy_combined_0_{t_max}.png"
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(filename_en, dpi=300, bbox_inches='tight')
        plt.close(fig_en)
        print(f"Saved {filename_en}")

    # 3. SYSTEM PARAMETERS COMBINED GRAPH
    # Save three versions of parameters combined plots: 300s, 600s, 2000s
    for t_max in [300, 600, 2000]:
        print(f"Generating combined parameters plot for t_max = {t_max}s...")
        fig_param, axes_param = plt.subplots(2, 2, figsize=(15, 10))
        
        # Style all axes consistently
        for ax in axes_param.flat:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#718096')
            ax.spines['bottom'].set_color('#718096')
            ax.grid(True, linestyle='--', alpha=0.5, color=COLORS['grid'])
        
        # Amplitude Plot (Top-Left)
        axes_param[0, 0].plot(t, amplitude, color=COLORS['amplitude'], linewidth=1.5, label=r'Amplitude $A$')
        axes_param[0, 0].set_title('Amplitude vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_param[0, 0].set_xlabel('Time (s)', fontsize=10)
        axes_param[0, 0].set_ylabel(r'Amplitude $A$ (rad)', fontsize=10)
        axes_param[0, 0].set_xlim(0, t_max)
        axes_param[0, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Angular Frequency Plot (Top-Right)
        axes_param[0, 1].plot(t, omega, color=COLORS['omega'], linewidth=1.5, label=r'Angular Frequency $\omega$')
        axes_param[0, 1].set_title('Angular Frequency vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_param[0, 1].set_xlabel('Time (s)', fontsize=10)
        axes_param[0, 1].set_ylabel(r'Angular Frequency $\omega$ (rad/s)', fontsize=10)
        axes_param[0, 1].set_xlim(0, t_max)
        axes_param[0, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Frequency Plot (Bottom-Left)
        axes_param[1, 0].plot(t, freq, color=COLORS['freq'], linewidth=1.5, label=r'Frequency $f$')
        axes_param[1, 0].set_title('Frequency vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_param[1, 0].set_xlabel('Time (s)', fontsize=10)
        axes_param[1, 0].set_ylabel(r'Frequency $f$ (Hz)', fontsize=10)
        axes_param[1, 0].set_xlim(0, t_max)
        axes_param[1, 0].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        # Period Plot (Bottom-Right)
        axes_param[1, 1].plot(t, T, color=COLORS['period'], linewidth=1.5, label=r'Period $T$')
        axes_param[1, 1].set_title('Period vs. Time', fontsize=12, fontweight='bold', pad=10)
        axes_param[1, 1].set_xlabel('Time (s)', fontsize=10)
        axes_param[1, 1].set_ylabel(r'Period $T$ (s)', fontsize=10)
        axes_param[1, 1].set_xlim(0, t_max)
        axes_param[1, 1].legend(loc='upper right', framealpha=0.9, facecolor='white', edgecolor='#E2E8F0')
        
        fig_param.suptitle(f'Harmonic Oscillator System Parameters (t = 0 to {t_max}s)', fontsize=15, fontweight='bold', y=0.98)
        
        filename_param = f"parameters_combined_0_{t_max}.png"
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(filename_param, dpi=300, bbox_inches='tight')
        plt.close(fig_param)
        print(f"Saved {filename_param}")

if __name__ == "__main__":
    main()
