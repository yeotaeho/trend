# 기술 파악 앱 (Flutter)

개인용 개발 트렌드 알림 앱이다. 앱 API v1(`/api/v1`)로 피드·판정 근거·걸러진 항목·찜·설정·프로필을 본다. 계약은 `docs/api/app-api-v1.md`, 화면 명세는 `docs/design/` 에 있다.

## 실행

`mobile/` 폴더에서 실행한다. 주입값은 `lib/core/config.dart` 의 세 가지다.

| 키 | 뜻 | 없을 때 |
|---|---|---|
| `API_BASE_URL` | 앱이 요청을 보낼 주소 | `http://localhost:8000/api/v1` |
| `APP_API_TOKEN` | `Authorization: Bearer` 로 보낼 토큰. 서버 `.env` 의 같은 키와 같아야 한다 | 빈 값(서버가 401) |
| `USE_FIXTURES` | `true` 면 서버 없이 `assets/fixtures/*.json` 으로 돈다 | `API_BASE_URL` 을 줬으면 `false`, 아니면 `true` |

```bash
flutter run                                          # fixture 모드 (서버 없이)
flutter run --dart-define-from-file=env/prod.json    # 운영 서버
```

어디에 붙었는지는 설정 탭의 앱 버전 줄에 보인다. `0.1.0 · fixture` 면 fixture, `0.1.0 · <호스트명>` 이면 그 서버다.

### env 파일

`env/<환경>.json` 은 git 에서 제외된다(`mobile/.gitignore` 의 `/env/`). 토큰이 들어 있으니 채팅·셸 인자·커밋에 적지 않는다.

```json
{"API_BASE_URL": "https://trend.yeotaeho.kr/api/v1", "APP_API_TOKEN": "<토큰>", "USE_FIXTURES": "false"}
```

토큰은 아래처럼 만들어 파일에 바로 쓴다. 화면에는 띄우지 않는다. 파일이 이미 있으면 덮어쓰지 않고 멈춘다.

```bash
python -c "import json,os,secrets; p='env/prod.json'; assert not os.path.exists(p), p+' exists'; os.makedirs('env',exist_ok=True); json.dump({'API_BASE_URL':'https://trend.yeotaeho.kr/api/v1','APP_API_TOKEN':secrets.token_urlsafe(32),'USE_FIXTURES':'false'},open(p,'w'),indent=2)"
```

같은 값을 서버 VM 의 `~/tech-radar/.env` 에 `APP_API_TOKEN=` 으로 넣는다. 토큰을 파이프로 넘길 때는 `print(..., end='')` 로 꺼낸다. Windows 파이썬의 `print` 는 파이프에 `\r\n` 을 쓰고, 받는 쪽(VM)에 `\r` 이 남으면 토큰이 어긋나 401 이 난다. PowerShell 5.1 파이프도 CRLF 를 붙이니 Git Bash 를 쓴다.

운영 서버에 붙는지는 Git Bash 에서 이렇게 본다.

```bash
T=$(python -c "import json; print(json.load(open('env/prod.json'))['APP_API_TOKEN'], end='')")
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $T" https://trend.yeotaeho.kr/api/v1/meta   # 200
unset T
```

### Android Studio

`mobile/` 폴더를 연다. 실행 설정(Run/Debug Configurations)의 Additional run args 에 `--dart-define-from-file=env/prod.json` 만 적는다. 'Store as project file' 로 저장하지 않는다. `.run/*.run.xml` 은 git 에서 제외되지 않는다.

## 릴리스 빌드와 폰 설치

```bash
flutter build apk --release --dart-define-from-file=env/prod.json
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

- APK 안에 토큰이 들어간다. Releases·Actions 아티팩트를 포함해 어디에도 올리지 않는다.
- 실서버 릴리스인데 주소가 https 가 아니거나 토큰이 비어 있으면 첫 화면이 뜨지 않는다(`releaseConfigProblem`).
- 설치가 `Requested internal only, but not enough space` 로 실패하면 기기·에뮬레이터 저장 공간 부족이다. 빌드 문제가 아니다.

## 테스트·확인

```bash
flutter analyze
TEMP='C:\tmp\fltemp' TMP='C:\tmp\fltemp' flutter test             # Git Bash
```

```powershell
$env:TEMP='C:\tmp\fltemp'; $env:TMP='C:\tmp\fltemp'; flutter test   # PowerShell
```

Windows 임시 폴더 경로에 한글이 있으면 flutter_tester 가 로드에 실패하므로 미리 만들어 둔 ASCII 경로(`C:\tmp\fltemp`)로 돌린다.

화면에 '알 수 없는 오류' 만 보이면 로그에서 원인을 본다. 조회 실패와 쓰기 실패는 원래 예외와 스택이 함께 찍힌다.

```bash
adb logcat -s flutter
```

## 토큰 교체

토큰이 샜거나 바꾸고 싶을 때 순서다.

1. `env/prod.json` 을 지우고 위 명령으로 새 토큰을 만든다.
2. 서버 VM 의 `~/tech-radar/.env` 에서 `APP_API_TOKEN` 을 새 값으로 바꾼다.
3. VM 에서 `cd ~/tech-radar && docker compose up -d --force-recreate --wait app` 한다. `restart` 로는 `.env` 가 다시 읽히지 않는다.
4. 위 curl 이 200 인지 본다.
5. 앱을 다시 빌드해 설치한다. 옛 APK 는 401 을 받는다.

## 실데이터에서 처음 보이는 것

- 카테고리 태그가 붙은 항목은 약 7%다(10-01 기준). 카테고리로 거르면 결과가 적다.
- 찜·주간 리포트·기기는 처음에 0건이다. 첫 주간 리포트는 월요일 09:00(Asia/Seoul)에 생긴다.
- 설정 탭의 04 관심사·05 알림 설정·06 수집 소스는 저장하면 운영 설정이 바로 바뀐다. 설정 관리 에픽 #30 이 배포될 때까지 앱에서 저장하지 않는다.
