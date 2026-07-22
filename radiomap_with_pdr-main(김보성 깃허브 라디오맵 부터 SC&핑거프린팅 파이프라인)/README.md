# radiomap_with_pdr

PDR(보행자 추측 항법) 궤적과 WiFi RSSI 시퀀스를 결합하여 실내 라디오맵(Radio Map)을 자동 생성하고, **Surface Correlation(SC)** 기반으로 위치를 추정하는 파이프라인입니다. IMU 센서(가속도계·자이로스코프)와 2.4GHz/5GHz WiFi RSSI 로그, 실내 도면 이미지를 입력으로 받아 RP(Reference Point) 단위 라디오맵을 만들고, 이를 이용해 사용자 위치를 추정합니다.

## 목차

- [파이프라인 개요](#파이프라인-개요)
- [폴더 구조](#폴더-구조)
- [요구 사항](#요구-사항)
- [실행 순서 (Quick Start)](#실행-순서-quick-start)
- [스크립트별 상세 설명](#스크립트별-상세-설명)
- [좌표계 규칙](#좌표계-규칙)
- [데이터 파일 스키마](#데이터-파일-스키마)
- [주요 설정값 튜닝 가이드](#주요-설정값-튜닝-가이드)
- [알려진 이슈 / 주의사항](#알려진-이슈--주의사항)

---

## 파이프라인 개요

전체 흐름은 8단계로 구성되며, 각 단계는 별도 스크립트(또는 노트북)로 분리되어 있고 파일 이름 앞의 숫자가 실행 순서를 의미합니다.

```
0. (선택) PDR 스텝 검출 디버깅
        │
1. IMU → PDR 궤적 추정 + WiFi RSSI 시간 매칭
        │  (1_pdrWiFiMerge.py)
        ▼
2. 도면 이미지에서 실제 이동 경로(코너) 좌표 클릭 수집
        │  (2_getTruePath.py)
        ▼
3. PDR 궤적을 실제 코너 좌표에 맞춰 보정 (Map Matching)
        │  (3_pdrMapMatching.py)
        ▼
4. 도면 위에 RP(Reference Point) 격자 좌표 생성
        │  (4_1_getRP_fingerprinting.py 또는 4_2_getRP_SC.py)
        ▼
5. 보정된 PDR 좌표 + RSSI를 RP에 매핑하여 라디오맵 생성
        │  (5_makeRadioMap.py)
        ▼
6. SC(Surface Correlation) 기반 위치 추정 (검증용)
        │  (6_SC.ipynb)
        ▼
7. 라디오맵 2D/3D 시각화
           (7_라디오맵2D시각화.py, 7_라디오맵3D시각화.py)
```

이 저장소의 8단계 구성은 다음 개념과 대응됩니다.

| # | 개념 | 대응 스크립트 |
|---|------|----------------|
| 1 | 데이터 수집 | `data/*.csv` (IMU, RSSI 로그, 외부에서 수집됨) |
| 2 | PDR 계산 후 WiFi와 결합 | `1_pdrWiFiMerge.py` |
| 3 | 도면에서 true position 픽셀좌표 추출 | `2_getTruePath.py` |
| 4 | 픽셀당 미터 계산 | `2_getTruePath.py` / `4_1`, `4_2` 내 calibration |
| 5 | 미터좌표계로 변환 | 동일 스크립트 내 `px_to_meter()` |
| 6 | PDR-true position 오차 파악 → 맵매칭 | `3_pdrMapMatching.py` |
| 7 | 도면에 RP 자동 생성 (간격 수동 설정) | `4_1_getRP_fingerprinting.py`, `4_2_getRP_SC.py` |
| 8 | RP 근접 WiFi 벡터 병합(RSSI 평균, -100 제외) | `5_makeRadioMap.py` |

---

## 폴더 구조

```
radiomap_with_pdr-main/
├── 0_pdr_디버깅용.py              # PDR 스텝 검출/헤딩 계산 디버깅 (플롯 다수)
├── 0_testPDR.ipynb                # PDR 테스트 노트북
├── 1_pdrWiFiMerge.py              # IMU→PDR 계산 + WiFi RSSI 시간창 평균 결합
├── 2_getTruePath.py               # 도면 클릭 기반 실측 경로(코너) 좌표 추출 (연속 폴리라인)
├── 3_pdrMapMatching.py            # PDR 궤적을 실측 코너 선분에 투영(보정)
├── 4_1_getRP_fingerprinting.py    # RP 좌표 생성 (2점씩 페어 클릭 → 구간별 보간)
├── 4_2_getRP_SC.py                # RP 좌표 생성 (폴리곤 ROI → 내부 격자 생성)
├── 5_makeRadioMap.py              # 보정 PDR+RSSI → RP별 라디오맵 (보간/이웃 평균 포함)
├── 6_SC.ipynb                     # Surface Correlation 위치 추정 + 도면 위 시각화
├── 7_라디오맵2D시각화.py           # 특정 AP의 RSSI 2D 히트맵 + PDR 경로 오버레이
├── 7_라디오맵3D시각화.py           # 대표 AP 5개의 RSSI 3D Surface Plot
├── radio_map.csv                  # (5단계 산출물) 최종 라디오맵
├── data/                          # 원본 입력 데이터
│   ├── 20260709_204218_PDR_RF.csv     # IMU + WiFi 통합 원시 로그 (스마트폰 수집)
│   ├── imu.csv                        # IMU 전용 로그 (가속도/자이로)
│   ├── rssi_2ghz.csv                  # 2.4GHz WiFi RSSI 로그
│   ├── rssi_5ghz.csv                  # 5GHz WiFi RSSI 로그
│   └── 공학관3층_동측_도면.png         # 실내 도면 이미지 (캘리브레이션 기준)
└── temp_data/                     # 중간 산출물 (파이프라인 실행 시 자동 생성)
    ├── pdr_WiFi.csv                    # (1단계 산출물) PDR+RSSI 결합
    ├── node.csv                        # (2단계 산출물) 실측 코너 좌표
    ├── node_preview.png                # 2단계 클릭 결과 미리보기
    ├── pdr_WiFi_map_matched.csv        # (3단계 산출물) 맵매칭 보정 좌표 포함
    ├── rp_pos.csv                      # (4단계 산출물) RP 격자 좌표
    ├── roi_polygon_preview.png         # 4_2 ROI 폴리곤 미리보기
    ├── roi_grid_points_preview.png     # 4_2 격자점 미리보기
    ├── calibration.json                # 도면 캘리브레이션 정보 (m/px, 원점 등)
    └── test_pdr_WiFi.csv               # 별도 테스트용 PDR+WiFi 결합 데이터
```

---

## 요구 사항

Python 3.9+ 권장. 아래 패키지가 필요합니다.

```bash
pip install numpy pandas matplotlib scipy opencv-python pillow
```

- `opencv-python` (`cv2`): 도면 클릭 수집 GUI(줌/팬/클릭), 이미지 저장 — **로컬 디스플레이 환경 필요** (원격 서버/헤드리스 환경에서는 실행 불가)
- `scipy`: `5_makeRadioMap.py`의 `LinearNDInterpolator` 선형 보간 (없으면 자동 스킵)
- `pillow`: `4_2_getRP_SC.py`의 한글 텍스트 오버레이 (`ImageFont`, `ImageDraw`)
- Jupyter/JupyterLab: `0_testPDR.ipynb`, `6_SC.ipynb` 실행용

Windows에서 `4_2_getRP_SC.py`는 한글 폰트로 `맑은 고딕(malgun.ttf)` 또는 `나눔고딕`을 찾습니다. 다른 OS에서는 폰트를 못 찾으면 영문 OpenCV 기본 폰트로 자동 대체됩니다.

---

## 실행 순서 (Quick Start)

작업 디렉토리는 항상 `radiomap_with_pdr-main/` 루트 기준입니다 (`BASE_DIR = os.getcwd()`).

```bash
cd radiomap_with_pdr-main

# 1) IMU → PDR 계산 + WiFi 결합
python 1_pdrWiFiMerge.py
# → temp_data/pdr_WiFi.csv 생성

# 2) 도면에서 실제 이동 경로(코너) 좌표 클릭 수집 (GUI)
python 2_getTruePath.py
# → temp_data/node.csv, node_preview.png 생성
# 조작법: 좌클릭=점 추가, z=undo, 휠=줌, 우클릭 드래그=팬, Enter=완료, ESC=종료

# 3) PDR 궤적을 실제 코너 좌표로 맵매칭
python 3_pdrMapMatching.py
# → temp_data/pdr_WiFi_map_matched.csv 생성 (+ matplotlib 결과 플롯)

# 4) RP(격자) 좌표 생성 — 목적에 따라 둘 중 하나 선택
python 4_1_getRP_fingerprinting.py   # 경로(선분) 페어 기반 1m 간격 보간
#   또는
python 4_2_getRP_SC.py               # ROI 폴리곤 내부 1m 격자 (SC 방식 권장)
# → temp_data/rp_pos.csv 생성

# 5) 라디오맵 생성
python 5_makeRadioMap.py
# → radio_map.csv 생성

# 6) SC 기반 위치 추정 검증 (Jupyter)
jupyter notebook 6_SC.ipynb

# 7) 시각화 (선택)
python 7_라디오맵2D시각화.py    # 특정 MAC의 2D 히트맵
python 7_라디오맵3D시각화.py    # 대표 AP 5개 3D Surface
```

> ⚠️ 사용자 메모리(`NNL 연구실`)에 따르면 **JPNT/IPNT는 SC 방식**, **AI융합연구원은 WiFi RSSI 핑거프린팅 방식**을 사용합니다. RP 생성 시 `4_2_getRP_SC.py`(SC용 ROI 폴리곤 격자)와 `4_1_getRP_fingerprinting.py`(핑거프린팅용 경로 기반 보간)를 목적에 맞게 선택해야 합니다.

---

## 스크립트별 상세 설명

### `0_pdr_디버깅용.py`
`imu.csv`를 로드해 PDR 계산 과정을 시각적으로 디버깅하는 스크립트.
- 가속도 노름(`sqrt(ax²+ay²+az²)`)에 4차 Butterworth 저역통과 필터(cutoff 3Hz, fs=50Hz) 적용
- `scipy.signal.find_peaks`로 스텝(피크) 검출 (`height=1.1`, `distance=20 샘플`)
- 피치/롤 보정 후 자이로 z축을 적분해 헤딩 계산, 스텝 길이 0.7m 고정으로 (x, y) 궤적 생성
- 헤딩 변화가 60°를 넘으면 회전(turn) 지점으로 기록
- 스텝 검출 결과, 헤딩 누적, 최종 궤적을 각각 matplotlib으로 플롯

### `1_pdrWiFiMerge.py`
`0_pdr_디버깅용.py`의 PDR 로직을 함수화하고, WiFi RSSI와 시간 기준으로 결합하는 실사용 스크립트.
- `load_sensor()`: `imu.csv` 로드, 컬럼을 `time, board_time, ax, ay, az, gx, gy, gz, rotation_hint`로 표준화
- `pdr()`: 스텝 검출 → 헤딩 계산 → (x, y) 좌표 생성. 반환값에 `pdr_df`(time, step_no, sample_idx, x, y, is_turn) 포함
- `load_wifi_rssi()`: `rssi_2ghz.csv` / `rssi_5ghz.csv` 로드 (첫 컬럼을 시간으로 인식)
- `average_wifi_in_time_window()`: 각 PDR 스텝 시각 기준 **±0.5초** 창 안의 RSSI를 AP별 평균 (단, `-100`은 미관측으로 보고 평균에서 제외, 창 안에 값이 없으면 `-100`으로 채움)
- 2.4GHz/5GHz에 동일 MAC이 있으면 `_2g` / `_5g` 접미사로 컬럼명 충돌 방지
- **출력**: `temp_data/pdr_WiFi.csv` (컬럼: `time, x, y, is_turn, <MAC1>, <MAC2>, ...`)

주요 파라미터: `STEP_LENGTH=0.7`(m), `FS=50`(Hz), `height=1.1`(스텝 검출 임계값), `window_sec=0.5`

### `2_getTruePath.py`
도면 이미지를 열어 **사용자가 실제로 걸은 경로(코너 지점들)**를 순서대로 클릭해 미터 좌표로 저장.
- 캘리브레이션: 도면에서 실제 길이를 아는 두 점을 클릭 → `m_per_px` 산출
- 원점은 이미지 좌측 상단 `(0,0)` 고정, `+X`는 오른쪽. `ENU_Y_AXIS=True`이면 `+Y`는 이미지 위쪽(즉, `y_m = -raw_y_m`)
- 이후 원하는 만큼 점을 순서대로 클릭 (경로 순서대로 연결선 표시) → Enter로 종료
- **출력**: `temp_data/node.csv` (`index, x_m, y_m, pixel_x, pixel_y`), `temp_data/node_preview.png`
- `3_pdrMapMatching.py`가 이 `node.csv`를 turn point 기준선으로 사용하므로, **`is_turn=1`으로 표시된 PDR 스텝 개수와 여기서 찍는 점 개수가 반드시 일치**해야 함

기본 설정: `KNOWN_LENGTH_M=3.5`, `FLOOR_MAP_IMAGE_NAME="data/공학관3층_동측_도면.png"`

### `3_pdrMapMatching.py`
1단계의 원본 PDR 궤적을 2단계에서 찍은 실측 코너 좌표(node.csv)에 맞춰 **구간별 투영 보정**.
- `pdr_WiFi.csv`의 `is_turn==1`인 인덱스를 turn point로 사용
- 각 turn 구간마다 PDR 누적 이동거리 비율을 계산해, 해당 비율만큼 실제 node 선분 위로 좌표를 재배치 (선형 투영) → 복도의 곡률 오차 제거, 직선 구간을 직선으로 강제 보정
- 첫 turn 이전/마지막 turn 이후 구간은 각각 첫/마지막 node 좌표로 고정
- **출력**: `temp_data/pdr_WiFi_map_matched.csv` (`time, original_x, original_y, x, y, is_turn, <MAC...>`) — `x, y`가 보정 좌표, `original_x/y`는 원본 PDR 좌표
- 원본 궤적 vs 보정 궤적 vs turn point를 matplotlib으로 비교 플롯

### `4_1_getRP_fingerprinting.py`
**핑거프린팅 방식**용 RP 좌표 생성 도구. 도면 위에 점을 **2개씩 짝(pair)**으로 클릭하면, 각 짝 사이만 지정 간격(기본 1m)으로 보간해 RP를 생성 (짝과 짝 사이(2-3번째 점 등)는 연결하지 않음 → 여러 개의 독립된 경로 구간을 만들 수 있음).
- 끝점이 마지막 보간점과 `MIN_END_POINT_DISTANCE_M`(기본 0.5m)보다 가까우면 끝점 생략
- **출력**: `temp_data/rp_pos.csv` (`index, pair_id, point_type, x_m, y_m, pixel_x, pixel_y`), `rp_pos_preview.png`

### `4_2_getRP_SC.py`
**SC(Surface Correlation) 방식**용 RP 좌표 생성 도구. 절차:
1. 캘리브레이션(치수선 2점 클릭)
2. **ROI 폴리곤**(오목 형태 가능) 꼭짓점을 여러 번 클릭 후 Enter
3. ROI 내부를 `GRID_M`(기본 1.0m) 간격의 정격자로 채우고, `cv2.pointPolygonTest`로 폴리곤 내부에 속하는 격자점만 채택
- 좌표계: 원점 좌측 상단, `+X` 오른쪽, 원본 픽셀 `+Y`는 아래쪽. `FLIP_Y_BEFORE_SAVE=True`이면 **CSV 저장 직전에만** `y_m = -y_m` 적용 (calibration.json에는 원본/저장본 둘 다 기록)
- 한글 안내 문구는 PIL로 렌더링(윈도우 폰트 우선 탐색), 실패 시 OpenCV 기본 폰트로 대체
- **출력**: `temp_data/rp_pos.csv` (`x_m, y_m, pixel_x, pixel_y`), `temp_data/calibration.json`, `roi_polygon_preview.png`, `roi_grid_points_preview.png`

> `4_1`과 `4_2`는 **둘 다 `rp_pos.csv`라는 동일 파일명**으로 저장되므로 같은 세션에서 두 개를 순서대로 실행하면 서로 덮어씁니다. 목적(핑거프린팅 vs SC)에 맞는 스크립트 하나만 실행하거나, 파일을 별도 백업해두어야 합니다. 또한 두 스크립트가 만드는 `x_m, y_m` 좌표계 규칙이 다르므로([좌표계 규칙](#좌표계-규칙) 참고) 혼용하지 않도록 주의하세요.

### `5_makeRadioMap.py`
`rp_pos.csv`(RP 마스터 좌표)와 `pdr_WiFi_map_matched.csv`(보정된 PDR+RSSI)를 결합해 최종 라디오맵을 생성. 3단계 채움 로직:
1. **PDR 직접 채움**: 각 RP를 중심으로 반경 `SEARCH_RADIUS_M`(기본 0.5m) 내의 PDR 샘플들을 모아 AP별 RSSI를 평균 (`-100`은 평균에서 제외, 유효값이 없으면 `-100` 유지)
2. **선형 보간**: PDR로 채워지지 않은 RP에 대해, PDR로 채워진 RP 중 해당 AP 값이 존재하는 지점들을 기준점으로 `scipy.interpolate.LinearNDInterpolator` 적용 (기준점 3개 미만이면 스킵)
3. **상하좌우 이웃 평균**: 선형 보간 후에도 `-100`으로 남은 RP는 격자 간격(`GRID_STEP_M=1.0`, 허용오차 `GRID_TOL_M=0.15`) 기준 상/하/좌/우 인접 RP의 평균으로 채움
- MAC 컬럼은 정규식(`^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(/.*)?$`)으로 자동 인식
- 디버그 컬럼 `is_pdr_filled, near_sample_count, linear_filled_ap_count, neighbor_filled_ap_count` 포함
- **출력**: `radio_map.csv` (`x, y, pixel_x, pixel_y, is_pdr_filled, ..., <MAC1>, <MAC2>, ...`)

### `6_SC.ipynb`
논문(`Novel indoor fingerprinting method based on RSS sequence matching`, Shin et al., 2023)에서 제안된 **User Mask ↔ Radio Map 상관도 매칭** 방식을 직접 구현/검증하는 노트북.
- **셀 0 (핵심 로직)**:
  - `BUFFER_SIZE=10` 스텝 분량의 최근 PDR 궤적 + RSSI 시퀀스로 URS(User RSSI Surface, 논문의 User Mask에 대응)를 동적 생성 (`generate_single_urs_dynamic`)
  - 헤딩 미지수 문제를 해결하기 위해 현재 헤딩 기준 `±1°, ±2°`(`DELTA_HEADING=1.0`) 5개 후보 각도로 세그먼트를 회전(`rotate_path`)시켜 각각 URS 생성
  - `calculate_correlation()`: URS를 라디오맵 전체 위로 슬라이딩하며 **SAD(Sum of Absolute Difference)** 최솟값 위치를 탐색 (논문의 RCC/상관계수 대신 절대오차 합 기반 매칭 사용)
  - 매 스텝마다 최적 각도/위치를 갱신하고, `CURRENT_HEADING`을 다음 스텝의 기준으로 사용 (헤딩 드리프트 보정)
  - `radio_map.csv`와 `pdr_WiFi.csv`의 **공통 AP만** 사용
- **셀 1**: `calibration.json`을 읽어 라디오맵/AI-PDR 경로/SC 추정 경로를 실제 도면 이미지 위에 겹쳐 시각화

주요 파라미터: `BUFFER_SIZE=10`(User Mask에 포함할 최근 스텝 수), `DELTA_HEADING=1.0`(헤딩 탐색 간격), `INITIAL_HEADING=-180.0`, `MISSING_RSSI=-100.0`

### `7_라디오맵2D시각화.py`
`radio_map.csv`에서 지정한 `TARGET_MAC` 하나의 RSSI 분포를 2D 사각형 격자(Rectangle patch)로 컬러맵 표시하고, `pdr_WiFi_map_matched.csv`의 보정된 PDR 경로(시작점/끝점 마커 포함)를 오버레이. 격자 간격은 좌표값 최소 간격을 자동 추정.

### `7_라디오맵3D시각화.py`
`radio_map.csv`에서 유효 관측치 개수(`valid_count`)와 평균 RSSI 기준으로 대표 AP 상위 `TOP_N=5`개를 자동 선정(또는 `TARGET_MACS`로 직접 지정)하여, 각각 `pivot_table` → `meshgrid` → `plot_surface`로 3D RSSI 표면 + 등고선을 그림.

---

## 좌표계 규칙

스크립트마다 좌표계 정의가 미묘하게 다르므로 혼용 시 주의가 필요합니다.

| 스크립트 | 원점 | +X | +Y (원본 픽셀 기준) | 저장 시 Y 반전 여부 |
|---|---|---|---|---|
| `2_getTruePath.py` | 이미지 좌측 상단 | 오른쪽 | `ENU_Y_AXIS=True` → 위쪽(ENU 방식, 즉 `y_m=-raw_y_m`) | 계산 시점에 이미 반영 |
| `4_1_getRP_fingerprinting.py` | 이미지 좌측 상단(고정) | 오른쪽(고정) | `ENU_Y_AXIS=True` → 위쪽 | 계산 시점에 이미 반영 |
| `4_2_getRP_SC.py` | 이미지 좌측 상단(고정) | 오른쪽(고정) | 아래쪽(원본 그대로) | **CSV 저장 직전에만** `FLIP_Y_BEFORE_SAVE=True` → `y_m=-y_m` 반영, `calibration.json`에 원본/저장본 둘 다 기록 |

**PDR 좌표계**: `1_pdrWiFiMerge.py`의 PDR은 `(0,0)`에서 시작해 헤딩 적분값(`arctan2` 기반, 도면과 무관한 자체 좌표계)으로 전진하며, `3_pdrMapMatching.py` 단계에서 비로소 도면의 실측 좌표계로 정렬됩니다. `6_SC.ipynb`에는 `PDR_SHIFT_X=59.31065546324714`, `PDR_SHIFT_Y=-8.657145362647874` 같은 하드코딩된 이동값이 있는데, 이는 `node.csv`의 첫 번째 점(시작점) 좌표와 동일합니다 — 새 데이터셋으로 교체 시 반드시 `node.csv`의 시작점 좌표로 갱신해야 합니다.

---

## 데이터 파일 스키마

### 입력 (`data/`)
- **`imu.csv`**: `timestamp, board_ts_ms, ax, ay, az, gx, gy, gz, rotation_hint`
- **`rssi_2ghz.csv` / `rssi_5ghz.csv`**: `timestamp, <MAC1>, <MAC2>, ...` (값은 RSSI dBm, 결측은 빈 칸)
- **`20260709_204218_PDR_RF.csv`**: IMU(`acc_*, gyro_*, mag_*, grv_*`)와 WiFi(`WIFI_<mac>/<ssid>` 컬럼)가 한 파일에 통합된 원시 로그 (스마트폰 앱 수집본으로 추정, 파이프라인 스크립트에서 직접 사용되지는 않음 — 참고/검증용)
- **`공학관3층_동측_도면.png`**: 캘리브레이션 및 RP 생성의 기준이 되는 도면 이미지

### 중간 산출물 (`temp_data/`)
- **`pdr_WiFi.csv`**: `time, x, y, is_turn, <MAC1>, ...` — PDR 자체 좌표계, RSSI는 ±0.5초 평균
- **`node.csv`**: `index, x_m, y_m, pixel_x, pixel_y` — 실측 경로 코너 좌표 (도면 기준)
- **`pdr_WiFi_map_matched.csv`**: `time, original_x, original_y, x, y, is_turn, <MAC1>, ...` — `x,y`는 도면 좌표계로 보정된 좌표
- **`rp_pos.csv`**: `x_m, y_m, pixel_x, pixel_y` (4_1은 `index, pair_id, point_type` 추가 포함) — RP 격자 좌표
- **`calibration.json`** (4_2 산출) — 캘리브레이션 픽셀-미터 변환식, ROI 폴리곤, 격자 범위 등 메타데이터

### 최종 산출물
- **`radio_map.csv`**: `x, y, pixel_x, pixel_y, is_pdr_filled, near_sample_count, linear_filled_ap_count, neighbor_filled_ap_count, <MAC1>, <MAC2>, ...` — RP별(현재 112개 RP × 358개 MAC 컬럼) 최종 라디오맵. RSSI 결측은 `-100`.

---

## 주요 설정값 튜닝 가이드

| 파일 | 변수 | 기본값 | 의미 |
|---|---|---|---|
| `1_pdrWiFiMerge.py` | `STEP_LENGTH` | 0.7 (m) | 고정 보폭 |
| | `height` | 1.1 | 스텝(피크) 검출 가속도 임계값 |
| | `turn_angle_deg` | 60° | 회전(turn)으로 판단하는 헤딩 변화 임계값 |
| | `window_sec` | 0.5 (초) | PDR 스텝 시각 기준 WiFi 평균 창 크기 |
| `2_getTruePath.py` / `4_1` / `4_2` | `KNOWN_LENGTH_M` | 3.5 (m) | 도면 캘리브레이션 기준 실제 길이 |
| `4_1_getRP_fingerprinting.py` | `INTERPOLATION_INTERVAL_M` | 1.0 (m) | RP 간격 |
| | `MIN_END_POINT_DISTANCE_M` | 0.5 (m) | 끝점 포함 최소 거리 |
| `4_2_getRP_SC.py` | `GRID_M` | 1.0 (m) | ROI 내부 격자 간격 |
| `5_makeRadioMap.py` | `SEARCH_RADIUS_M` | 0.5 (m) | RP 주변 PDR 샘플 탐색 반경 |
| | `GRID_STEP_M` / `GRID_TOL_M` | 1.0 / 0.15 (m) | 이웃 평균 보정용 격자 간격/허용오차 |
| `6_SC.ipynb` | `BUFFER_SIZE` | 10 (스텝) | User Mask에 포함할 최근 궤적 길이 (사용자 메모리의 "대각선 길이 30m 최적" 논문 결과에 대응하는 파라미터이므로, 실제 필드 테스트 시 함께 튜닝 권장) |
| | `DELTA_HEADING` | 1.0° | 헤딩 탐색 간격 |

---

## 알려진 이슈 / 주의사항

1. **GUI 의존성**: `2_getTruePath.py`, `4_1_getRP_fingerprinting.py`, `4_2_getRP_SC.py`는 `cv2.imshow` 기반 인터랙티브 창을 사용하므로 SSH/헤드리스 서버에서는 실행되지 않습니다. 로컬 데스크톱 환경에서 실행해야 합니다.
2. **`rp_pos.csv` 파일명 충돌**: `4_1`과 `4_2`가 동일한 출력 파일명(`rp_pos.csv`)을 사용합니다. SC용과 핑거프린팅용 RP를 모두 보관하려면 실행 후 파일명을 수동으로 구분해 백업해야 합니다.
3. **`is_turn` 개수 불일치**: `3_pdrMapMatching.py`는 `pdr_WiFi.csv`의 `is_turn==1` 개수와 `node.csv`의 행 개수가 정확히 같아야 정상 동작합니다(`ValueError` 발생 조건). 2단계에서 도면을 클릭할 때 PDR이 감지한 회전 횟수와 실제로 꺾은 코너 개수를 맞춰야 합니다.
4. **`0_pdr_디버깅용.py`의 버그**: `WIFI_5GHZ_DATA_PATH`가 확장자 없이 `"rssi_5ghz"`로 정의되어 있어(파일명은 `rssi_5ghz.csv`), 해당 변수를 사용하는 코드가 있다면 오류가 납니다. 이 스크립트는 실제로는 WiFi 병합 로직 없이 PDR 디버깅만 수행하므로 영향은 제한적입니다.
5. **`PDR_SHIFT_X/Y` 하드코딩**: `6_SC.ipynb`의 좌표 이동값은 특정 데이터셋(`node.csv`의 시작점) 기준으로 하드코딩되어 있습니다. 새로운 수집 데이터로 교체 시 반드시 갱신이 필요합니다.
6. **`5_makeRadioMap.py`의 반복문 성능**: RP별로 `for _, rp in master_df.iterrows()` 및 `LinearNDInterpolator`를 AP마다 재생성하는 구조라, RP 수·AP 수가 커지면 (예: 358개 AP × 100+ RP) 실행 시간이 늘어날 수 있습니다. 현재 규모(RP 112개)에서는 문제없지만, 향후 RP 밀도를 높이거나 AP 수가 크게 늘어나면 벡터화 개선을 고려할 수 있습니다.
