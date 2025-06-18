# Haptic Ring Monitoring System

Izhikevich 뉴런 모델을 기반으로 한 햅틱 피드백 시뮬레이션 시스템입니다. 마우스 입력을 SA(Slow Adapting) 및 RA(Rapidly Adapting) 촉각 수용체의 반응으로 변환하여 실시간 오디오 피드백을 제공합니다.

## 시스템 구조

```
마우스 입력 → SpikeEncoder → 뉴런 시뮬레이션 → HapticRenderer → AudioPlayer → 오디오 출력
                                    ↓
                           실시간 그래프 시각화
```

## 주요 애플리케이션

### 1. main.py - 햅틱 연구용 시뮬레이터
- **목적**: 뉴런 모델 연구 및 햅틱 피드백 분석
- **프레임워크**: PyQt6 + Matplotlib
- **기능**:
  - 3개 뉴런의 실시간 막전위/회복변수 시각화 (SA, RA_Motion, RA_Click)
  - 7가지 재질별 햅틱 피드백 (Glass, Metal, Wood, Plastic, Fabric, Ceramic, Rubber)
  - 마우스 클릭/움직임을 뉴런 자극으로 변환
  - 키보드 단축키 (1-7: 재질 변경, R: 리셋, +/-: 볼륨 조절)

### 2. automotive_demo.py - 자동차 인터페이스 데모
- **목적**: 자동차 터치스크린 햅틱 인터페이스 시연
- **프레임워크**: Pygame
- **기능**:
  - 9개 자동차 제어 버튼 (AC, Heat, Fan, Defrost, Auto, Lock, Windows, Lights, Horn)
  - 플라스틱 재질 고정으로 일관된 햅틱 경험
  - 5채널 햅틱 피드백: SA(압력) + RA_Motion(움직임) + RA_Click(클릭) + RA_Hover(진입) + RA_Exit(이탈)
  - 버튼 영역에서만 햅틱 반응, 배경에서는 비활성화

### 3. simple_driving_simulator.py - 운전 시뮬레이터
- **목적**: MetaDrive 기반 1인칭 운전 시뮬레이션
- **프레임워크**: MetaDrive + Panda3D
- **기능**:
  - WASD 키보드 제어 (W: 전진, A: 좌회전, S: 후진, D: 우회전)
  - 1인칭 시점 운전 환경
  - 별도 AC 터치 패널과 연동
  - 자동 운전 모드 (입력 없을 시)

### 4. ac_touch_panel.py - 공조기 터치 패널
- **목적**: 운전 중 공조기 조작 시뮬레이션
- **프레임워크**: Tkinter
- **기능**:
  - 전원, 온도, 풍량, 모드 제어
  - 퀴즈 시스템으로 운전 중 주의분산 측정
  - 운전 시뮬레이터와 큐 기반 통신

## 핵심 모듈

### izhikevich_neuron.py
Izhikevich 뉴런 모델 구현
- 4개 파라미터 (a, b, c, d)로 다양한 뉴런 특성 모델링
- 막전위(v)와 회복변수(u)의 미분방정식 해법
- 스파이크 감지 및 리셋 메커니즘

### spike_encoder.py
마우스 입력을 뉴런 자극으로 변환
- SA 뉴런: 마우스 클릭 압력 시뮬레이션
- RA Motion 뉴런: 마우스 속도 변화 감지
- RA Click 뉴런: 클릭 on/off 이벤트 처리
- 재질별 거칠기 파라미터 적용

### haptic_renderer.py
뉴런 스파이크를 오디오 신호로 변환
- 기본 사인파 생성 및 재질별 특화 파형
- 7가지 재질별 고유 음향 특성:
  - Glass: 높은 배음, 고주파 노이즈
  - Metal: 비조화 배음, AM 변조
  - Wood: 부드러운 배음, 저주파 강화
  - Plastic: 사각파 성분, 인공적 특성
  - Fabric: 마찰 노이즈
  - Ceramic: 유리보다 둔한 소리
  - Rubber: 탄성적 변조
- 페이드인/아웃 및 볼륨 제어

### audio_player.py
실시간 오디오 재생 관리
- Pygame 기반 3채널 동시 재생
- 채널별 독립적 볼륨 제어
- 메모리 효율적인 사운드 캐싱

## 시스템 요구사항

### 필수 라이브러리
```bash
pip install PyQt6 matplotlib numpy pygame
```

### 선택적 라이브러리 (운전 시뮬레이터용)
```bash
pip install metadrive-simulator
```

## 실행 방법

### 1. 햅틱 연구 시뮬레이터
```bash
python main.py
```
- 마우스 클릭/드래그로 햅틱 피드백 체험
- 1-7 키로 재질 변경
- R 키로 시뮬레이션 리셋

### 2. 자동차 인터페이스 데모
```bash
python automotive_demo.py
```
- 버튼 위에 마우스 올리기: 호버 피드백
- 버튼 클릭: 클릭 피드백
- 버튼 위에서 마우스 이동: 질감 피드백

### 3. 운전 시뮬레이터 + AC 패널
```bash
# 터미널 1: 운전 시뮬레이터
python simple_driving_simulator.py

# 터미널 2: AC 터치 패널 (별도 실행)
python ac_touch_panel.py
```

## 설정 파라미터

### 뉴런 파라미터
- **SA 뉴런**: a=0.05, b=0.25, c=-65.0, d=6.0 (압력 감지)
- **RA Motion**: a=0.4, b=0.25, c=-65.0, d=1.5 (움직임 감지)
- **RA Click**: a=0.3, b=0.25, c=-65.0, d=6.0 (클릭 감지)

### 사운드 설정
- **SA**: 25Hz, 120ms, 압력 피드백
- **RA Motion**: 35Hz, 90ms, 속도 기반 볼륨
- **RA Click**: 50Hz, 70ms, 클릭 피드백
- **샘플링 레이트**: 44.1kHz

### 재질별 특성
- **Glass**: r=0.5, f=1.3, brightness=2.5
- **Metal**: r=1.0, f=1.1, resonance=1.8
- **Wood**: r=0.8, f=0.9, warmth=1.2
- **Plastic**: r=0.4, f=1.0, hardness=1.1
- **Fabric**: r=0.2, f=0.7, softness=1.5
- **Ceramic**: r=0.6, f=1.2, brittleness=1.4
- **Rubber**: r=0.3, f=0.8, elasticity=1.3

## 연구 활용

이 시스템은 다음 연구 분야에 활용 가능합니다:
- 햅틱 인터페이스 설계
- 뉴런 모델 기반 촉각 시뮬레이션
- 자동차 HMI 사용성 평가
- 운전 중 주의분산 연구
- 재질별 촉각 피드백 특성 분석

## 라이선스

이 프로젝트는 연구 및 교육 목적으로 개발되었습니다.
