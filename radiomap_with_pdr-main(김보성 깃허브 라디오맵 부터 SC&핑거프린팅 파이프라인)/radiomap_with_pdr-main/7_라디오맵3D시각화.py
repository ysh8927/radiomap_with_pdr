import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import re

from mpl_toolkits.mplot3d import Axes3D

# ============================================================
# 사용자 설정
# ============================================================
BASE_DIR = os.getcwd()
RADIO_MAP_PATH = os.path.join(BASE_DIR, "radio_map.csv")

X_COL = "x"
Y_COL = "y"

MISSING_RSSI = -100
TOP_N = 5

# 직접 보고 싶은 MAC이 있으면 여기에 지정
# None이면 자동으로 대표 5개 선택
TARGET_MACS = None

# 예시:
# TARGET_MACS = [
#     "00:40:5A:AF:98:B9",
#     "00:40:5A:AF:98:BB",
#     "00:40:5A:AF:98:BA",
#     "00:40:5A:AF:E1:99",
#     "58:86:94:AE:50:CA",
# ]


# ============================================================
# 1. Radio Map 불러오기
# ============================================================
radio_map = pd.read_csv(RADIO_MAP_PATH)

print("Radio map shape:", radio_map.shape)
print("Columns:", radio_map.columns.tolist()[:15], "...")


# ============================================================
# 2. MAC 컬럼 자동 추출
# ============================================================
mac_pattern = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")

mac_cols = [
    col for col in radio_map.columns
    if mac_pattern.match(str(col))
]

if len(mac_cols) == 0:
    raise ValueError("MAC 주소 형식의 AP 컬럼을 찾지 못했습니다.")

print(f"\n전체 AP MAC 개수: {len(mac_cols)}")


# ============================================================
# 3. 대표 MAC 5개 선택
#    - -100은 미측정값으로 제외
#    - valid_count가 많은 AP 우선
#    - 평균 RSSI가 강한 AP 우선
# ============================================================
rssi_df = radio_map[mac_cols].apply(pd.to_numeric, errors="coerce")
rssi_df = rssi_df.replace(MISSING_RSSI, np.nan)

ap_summary = pd.DataFrame({
    "valid_count": rssi_df.notna().sum(),
    "mean_rssi": rssi_df.mean(),
    "max_rssi": rssi_df.max(),
})

ap_summary = ap_summary.sort_values(
    by=["valid_count", "mean_rssi"],
    ascending=[False, False]
)

if TARGET_MACS is None:
    selected_macs = ap_summary.head(TOP_N).index.tolist()
else:
    selected_macs = TARGET_MACS

print("\n선택된 대표 MAC:")
print(ap_summary.loc[selected_macs])


# ============================================================
# 4. MAC별 3D Surface Plot 함수
# ============================================================
def plot_rssi_surface_for_mac(radio_map, target_mac):
    df = radio_map[[X_COL, Y_COL, target_mac]].copy()

    df[X_COL] = pd.to_numeric(df[X_COL], errors="coerce")
    df[Y_COL] = pd.to_numeric(df[Y_COL], errors="coerce")
    df[target_mac] = pd.to_numeric(df[target_mac], errors="coerce")

    # -100은 미측정값으로 처리
    df[target_mac] = df[target_mac].replace(MISSING_RSSI, np.nan)

    # 좌표 또는 RSSI가 없는 행 제거
    df = df.dropna(subset=[X_COL, Y_COL, target_mac]).copy()

    if len(df) == 0:
        print(f"[SKIP] {target_mac}: 유효한 RSSI 값이 없습니다.")
        return

    # pivot으로 2D grid 생성
    grid = df.pivot_table(
        index=Y_COL,
        columns=X_COL,
        values=target_mac,
        aggfunc="mean"
    )

    # x, y 정렬
    grid = grid.sort_index(axis=0)
    grid = grid.sort_index(axis=1)

    x_unique = grid.columns.to_numpy(dtype=float)
    y_unique = grid.index.to_numpy(dtype=float)

    X, Y = np.meshgrid(x_unique, y_unique)
    Z = grid.to_numpy(dtype=float)

    # NaN 마스킹
    Z_masked = np.ma.masked_invalid(Z)

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        X, Y, Z_masked,
        cmap="viridis",
        linewidth=0,
        antialiased=True,
        alpha=0.9
    )

    # 등고선 추가
    if np.isfinite(Z).any():
        z_min = np.nanmin(Z)
        ax.contour(
            X, Y, Z_masked,
            15,
            cmap="viridis",
            offset=z_min
        )

    ax.set_title(f"RSSI 3D Surface\n{target_mac}")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("RSSI (dBm)")

    fig.colorbar(
        surf,
        ax=ax,
        shrink=0.5,
        aspect=10,
        label="RSSI (dBm)"
    )

    ax.view_init(elev=40, azim=135)

    plt.axis("equal")
    plt.tight_layout()
    plt.show()


# ============================================================
# 5. 대표 MAC 5개 각각 시각화
# ============================================================
for mac in selected_macs:
    plot_rssi_surface_for_mac(radio_map, mac)