import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import re
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

mpl.rcParams["path.simplify"] = False

# ============================================================
# 사용자 설정
# ============================================================
BASE_DIR = os.getcwd()

RADIO_MAP_PATH = os.path.join(BASE_DIR, "radio_map.csv")
PDR_PATH = os.path.join(BASE_DIR, "temp_data", "pdr_WiFi_map_matched.csv")

# 보고 싶은 AP MAC 주소
TARGET_MAC = "00:40:5A:AF:E1:9A"

# Radio Map 좌표 컬럼
X_COL = "x"
Y_COL = "y"

# PDR 경로 좌표 컬럼
PDR_X_COL = "x"
PDR_Y_COL = "y"

# RSSI 결측값
MISSING_RSSI = -100

# -100도 표시할지 여부
SHOW_MISSING = True

# RSSI color range
VMIN = -100
VMAX = -30

# 컬러맵
CMAP = "viridis"

# 격자 칸 크기 비율
CELL_SCALE = 1.0

# PDR 경로 표시 여부
SHOW_PDR_PATH = True


# ============================================================
# MAC 컬럼 찾기 함수
# ============================================================
def find_mac_column(df, target_mac):
    target_mac = str(target_mac).strip().upper()

    for col in df.columns:
        if str(col).strip().upper() == target_mac:
            return col

    for col in df.columns:
        col_str = str(col).strip().upper()

        if col_str.startswith(target_mac + "/"):
            return col

    raise ValueError(f"TARGET_MAC에 해당하는 컬럼을 찾지 못했습니다: {target_mac}")


# ============================================================
# 좌표 간격 자동 추정 함수
# ============================================================
def estimate_grid_step(values):
    values = np.sort(np.unique(np.round(values.astype(float), 6)))

    if len(values) < 2:
        return 1.0

    diffs = np.diff(values)
    diffs = diffs[diffs > 1e-6]

    if len(diffs) == 0:
        return 1.0

    return float(np.min(diffs))


# ============================================================
# 데이터 로드
# ============================================================
radio_map_df = pd.read_csv(RADIO_MAP_PATH)
pdr_path_df = pd.read_csv(PDR_PATH)

if X_COL not in radio_map_df.columns:
    raise ValueError(f"radio_map_df에 {X_COL} 컬럼이 없습니다.")

if Y_COL not in radio_map_df.columns:
    raise ValueError(f"radio_map_df에 {Y_COL} 컬럼이 없습니다.")

if PDR_X_COL not in pdr_path_df.columns:
    raise ValueError(f"pdr_path_df에 {PDR_X_COL} 컬럼이 없습니다.")

if PDR_Y_COL not in pdr_path_df.columns:
    raise ValueError(f"pdr_path_df에 {PDR_Y_COL} 컬럼이 없습니다.")

target_col = find_mac_column(radio_map_df, TARGET_MAC)

print("선택된 AP 컬럼:", target_col)


# ============================================================
# RSSI 값 정리
# ============================================================
radio_map_df[target_col] = pd.to_numeric(
    radio_map_df[target_col],
    errors="coerce"
).fillna(MISSING_RSSI)

plot_df = radio_map_df.copy()

if not SHOW_MISSING:
    plot_df = plot_df[plot_df[target_col] != MISSING_RSSI].copy()

plot_df = plot_df.dropna(subset=[X_COL, Y_COL]).copy()

x = plot_df[X_COL].to_numpy(dtype=float)
y = plot_df[Y_COL].to_numpy(dtype=float)
rssi_values = plot_df[target_col].to_numpy(dtype=float)


# ============================================================
# PDR 경로 정리
# ============================================================
pdr_path_df[PDR_X_COL] = pd.to_numeric(
    pdr_path_df[PDR_X_COL],
    errors="coerce"
)

pdr_path_df[PDR_Y_COL] = pd.to_numeric(
    pdr_path_df[PDR_Y_COL],
    errors="coerce"
)

pdr_path_df = pdr_path_df.dropna(
    subset=[PDR_X_COL, PDR_Y_COL]
).copy()

pdr_x = pdr_path_df[PDR_X_COL].to_numpy(dtype=float)
pdr_y = pdr_path_df[PDR_Y_COL].to_numpy(dtype=float)

print("PDR 경로 포인트 개수:", len(pdr_path_df))


# ============================================================
# 격자 칸 크기 계산
# ============================================================
dx = estimate_grid_step(x) * CELL_SCALE
dy = estimate_grid_step(y) * CELL_SCALE

print("추정 격자 간격 dx:", dx)
print("추정 격자 간격 dy:", dy)


# ============================================================
# 시각화
# ============================================================
fig, ax = plt.subplots(figsize=(24, 6))

patches = []

for xi, yi in zip(x, y):
    rect = Rectangle(
        (xi - dx / 2, yi - dy / 2),
        dx,
        dy
    )
    patches.append(rect)

collection = PatchCollection(
    patches,
    cmap=CMAP,
    edgecolor="k",
    linewidth=0.25,
    zorder=1
)

collection.set_array(rssi_values)
collection.set_clim(VMIN, VMAX)

ax.add_collection(collection)

# colorbar
cbar = fig.colorbar(collection, ax=ax)
cbar.set_label("RSSI (dBm)")


# ============================================================
# PDR 경로 Overlay
# ============================================================
if SHOW_PDR_PATH and len(pdr_path_df) > 0:
    ax.plot(
        pdr_x,
        pdr_y,
        color="red",
        linewidth=2.0,
        marker="o",
        markersize=3,
        label="PDR Path",
        zorder=10
    )

    # 시작점
    ax.scatter(
        pdr_x[0],
        pdr_y[0],
        color="blue",
        marker="o",
        s=120,
        edgecolor="white",
        linewidth=1.0,
        label="PDR Start",
        zorder=11
    )

    # 끝점
    ax.scatter(
        pdr_x[-1],
        pdr_y[-1],
        color="red",
        marker="*",
        s=220,
        edgecolor="white",
        linewidth=1.0,
        label="PDR End",
        zorder=11
    )


# ============================================================
# 축 범위 설정
# - Radio Map과 PDR 경로를 모두 포함하도록 설정
# ============================================================
if SHOW_PDR_PATH and len(pdr_path_df) > 0:
    all_x = np.concatenate([x, pdr_x])
    all_y = np.concatenate([y, pdr_y])
else:
    all_x = x
    all_y = y

margin_x = dx
margin_y = dy

ax.set_xlim(all_x.min() - margin_x, all_x.max() + margin_x)
ax.set_ylim(all_y.min() - margin_y, all_y.max() + margin_y)


# pixel 좌표계면 이미지처럼 y축 뒤집기
if X_COL == "pixel_x" and Y_COL == "pixel_y":
    ax.invert_yaxis()


# ============================================================
# 축 / 제목 설정
# ============================================================
ax.set_title(f"RSSI Radio Map with PDR Path\nAP: {target_col}", fontsize=16)
ax.set_xlabel(X_COL)
ax.set_ylabel(Y_COL)

ax.set_xticks(
    np.arange(
        np.floor(all_x.min()),
        np.ceil(all_x.max()) + 1,
        1
    )
)

ax.set_yticks(
    np.arange(
        np.floor(all_y.min()),
        np.ceil(all_y.max()) + 1,
        1
    )
)

ax.grid(True, linestyle="--", alpha=0.25)

ax.axis("equal")
ax.legend(loc="upper right")

plt.tight_layout()
plt.show()


