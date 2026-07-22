import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

from scipy.signal import butter, filtfilt, find_peaks

BASE_DIR = os.getcwd()
IMU_DATA_PATH = os.path.join(BASE_DIR, "data", "imu.csv")
WIFI_2_4GHZ_DATA_PATH = os.path.join(BASE_DIR, "data", "rssi_2ghz.csv")
WIFI_5GHZ_DATA_PATH = os.path.join(BASE_DIR, "data", "rssi_5ghz")
OUTPUT_DATA_PATH = os.path.join(BASE_DIR, "temp_data")
OUTPUT_DATA_NAME = 'pdr_WiFi.csv'

STEP_LENGTH = 0.7
FS = 50

def load_sensor(file_path):
    df = pd.read_csv(file_path)
    
    df.columns = [
        'time', 'board_time',
        'ax', 'ay', 'az',
        'gx', 'gy', 'gz',
        'rotation_hint'
    ]
    
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    start_dt = df["time"].iloc[0]
    df["Elapsed Time"] = (df["time"] - start_dt).dt.total_seconds()
    
    return df 

def pdr(df, fs=50, step_length=0.7):
    #time_sec = (df["time"] - df["time"].iloc[0]).values / 1e9
    
    acc_norm = np.sqrt(
        df["ax"]**2 +
        df["ay"]**2 +
        df["az"]**2
    )
    
    nyquist = 0.5 * fs
    normal_cutoff = 3.0 / nyquist

    b, a = butter(4, normal_cutoff, btype="low", analog=False)
    acc_norm_smoothed = filtfilt(b, a, acc_norm)
    print(len(acc_norm_smoothed))
    
    height = 1.1

    peaks, _ = find_peaks(
        acc_norm_smoothed,
        height=height,
        distance=20
    )
    
    plot_start = 0
    plot_end = 1000

    plot_peaks = peaks[
        (peaks >= plot_start) & 
        (peaks < plot_end)
    ]

    plt.figure(figsize=(14, 5))

    plt.plot(
        np.arange(plot_start, plot_end),
        acc_norm_smoothed[plot_start:plot_end],
        label="Smoothed Acc Norm"
    )

    plt.scatter(
        plot_peaks,
        acc_norm_smoothed[plot_peaks],
        s=40,
        label="Detected Step Peaks",
        zorder=3
    )

    plt.axhline(
        y=height,
        linestyle="--",
        c='red',
        label=f"Threshold = {height}"
    )

    plt.xlabel("Sample Index")
    plt.ylabel("Acceleration Norm")
    plt.title("Step Detection Result")
    plt.grid(True)
    plt.legend()
    plt.show()

    print("Detected steps:", len(peaks))
    
    ax = df["ax"].values
    ay = df["ay"].values
    az = df["az"].values

    pitch = np.arctan2(ay, az)
    roll = np.arctan2(-ax, np.sqrt(ay**2 + az**2))
    
    gx = df["gx"].values
    gy = df["gy"].values
    gz = df["gz"].values
    
    gyro_corr = np.zeros((len(df), 3))
    
    for i in range(len(df)):
        cos_p = np.cos(pitch[i])
        sin_p = np.sin(pitch[i])
        cos_r = np.cos(roll[i])
        sin_r = np.sin(roll[i])
        
        R_inv_pitch = np.array([
            [1,     0,      0],
            [0, cos_p, -sin_p],
            [0, sin_p,  cos_p]
        ])
        
        R_inv_roll = np.array([
            [ cos_r, 0, sin_r],
            [     0, 1,     0],
            [-sin_r, 0, cos_r]
        ])
        
        R_tilt = R_inv_roll @ R_inv_pitch 
        
        gyro_vector = np.array([gx[i], gy[i], gz[i]])
        gyro_corr[i] = R_tilt @ gyro_vector
        
    gz_corr = gyro_corr[:, 2]
    
    heading = np.cumsum(gz_corr) / FS
    rad_heading = np.radians(heading)
    
    plt.plot(heading)
    plt.show()
    
    x_pos = [0]
    y_pos = [0]

    turn_idx = [0]

    prev_heading = None

    for step_count, step_idx in enumerate(peaks, start=1):
        psi = rad_heading[step_idx]

        if prev_heading is not None:
            heading_diff = psi - prev_heading
            
            # -pi ~ pi 범위로 정규화
            heading_diff = np.arctan2(np.sin(heading_diff), np.cos(heading_diff))

            if np.abs(heading_diff) > np.radians(60):
                turn_idx.append(step_count-1)

        prev_heading = psi

        delta_x = step_length * np.cos(psi)
        delta_y = step_length * np.sin(psi)
        
        x_pos.append(x_pos[-1] + delta_x)
        y_pos.append(y_pos[-1] + delta_y)
    
    last_idx = len(x_pos) - 1
    turn_idx.append(last_idx)
        
    return np.array(x_pos), np.array(y_pos), np.array(turn_idx)
    
    
df = load_sensor(IMU_DATA_PATH)
x, y, idx = pdr(df)

x = np.asarray(x)
y = np.asarray(y)
idx = np.asarray(idx, dtype=int)

# idx가 x, y 범위 안에 있는 것만 사용
valid_idx = idx[(idx >= 0) & (idx < len(x))]

plt.figure(figsize=(8, 8))

# 전체 PDR 궤적
plt.plot(x, y, '.-', label='PDR trajectory')

# idx에 해당하는 좌표만 빨간색으로 표시
plt.scatter(
    x[valid_idx],
    y[valid_idx],
    color='red',
    s=60,
    zorder=3,
    label='Selected step points'
)

# 점 옆에 걸음 번호 표시
for i in valid_idx:
    plt.text(
        x[i],
        y[i],
        str(i),
        fontsize=9,
        color='red'
    )

plt.axis('equal')
plt.grid(True)
plt.legend()
plt.show()

    
    