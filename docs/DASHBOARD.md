# rmf-web ダッシュボード(任意)

ブラウザからタスクを投入し、フリートを監視するための rmf-web を
コンテナで起動する手順。CLI(`rmf_demos_tasks`)と RViz だけでも運用できるので、
この構成は任意で、使わなくても本パッケージの動作には影響しない。

## 構成

ROS 2 スタックはホストでそのまま動かし、rmf-web だけをコンテナ化する。
`toio_rmf.launch.py` には手を入れず、`server_uri` を渡すだけで接続される。

```mermaid
flowchart LR
  subgraph host["ホスト(Ubuntu 24.04 + ROS 2 Jazzy)"]
    RMF["toio_rmf.launch.py<br/>RMFコア + フリートアダプタ"]
    VIZ["schedule_visualizer_node<br/>トラジェクトリサーバ :8006"]
  end
  subgraph containers["コンテナ(network_mode: host)"]
    API["api-server :8000<br/>ghcr.io の公開イメージ"]
    DASH["dashboard :3000<br/>本リポジトリでビルド"]
  end
  BROWSER["ブラウザ"]

  RMF <-->|"ws://localhost:8000/_internal"| API
  RMF --> VIZ
  BROWSER -->|":3000"| DASH
  BROWSER -->|"REST / WebSocket :8000"| API
  BROWSER -->|":8006"| VIZ
```

トラジェクトリサーバ(8006)は `rmf_visualization` の `schedule_visualizer_node`
が既定で立てるため、`toio_rmf.launch.py` を起動していればすでに動いている
(`rmf_headless:=true` にしても抑止されるのは RViz だけ)。

## 前提

- Ubuntu 24.04、Docker Engine + Compose プラグイン
  (`sudo apt install docker.io docker-compose-v2` など)
- `docs/SETUP.md` の環境構築が済んでいること
- ダッシュボードのベースイメージ `minimal-rmf` は **linux/amd64 のみ**公開されている
- **この compose 構成は Docker Desktop for Mac / Windows では使えない。**
  コンテナが Linux VM の別ネットワーク名前空間で動くため DDS が届かず、
  タスク投入もマップ表示もできない。さらに `ROS_DOMAIN_ID` をホストと揃えると
  **ホスト側の ROS 2 が起動しなくなる**(下記トラブルシュート参照)。
  macOS では代わりに「[コンテナを使わない構成](#コンテナを使わない構成)」を使う

## 起動手順

### 1. ダッシュボードイメージをビルド(初回のみ)

```bash
cd ~/dev_ws/src/toio_rmf_bringup/docker
docker compose build dashboard
```

rmf-web の monorepo を取得して pnpm でビルドするため時間がかかる。
api-server 側は公開イメージをそのまま使うのでビルドは不要。

### 2. コンテナを起動

```bash
docker compose up -d
docker compose logs -f api-server   # 起動確認
```

### 3. ROS 2 スタックを `server_uri` 付きで起動

```bash
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py \
  mat:=a4 \
  server_uri:=ws://localhost:8000/_internal
```

シミュレーションの場合は `mat:=a3 run_sim:=true use_sim_time:=true` を加え、
api-server 側も `USE_SIM_TIME=true` で起動する(下記「設定」参照)。

### 4. ブラウザで開く

<http://localhost:3000>

Map タブにマットと2台のキューブが表示され、Tasks タブから patrol タスクを投入できる。

![rmf-webダッシュボードのRobotsタブ](images/10_dashboard_robots.png)
*Robots タブ ── `toio1` / `toio2` がフリート `toio` として並び、位置とバッテリ残量が
更新される([toio_rmf_tutorial 章10](https://github.com/atinfinity/toio_rmf_tutorial/blob/main/10_visualization.md)と共通の
スクリーンショット。シミュレーション実行時のため Battery は 100% 固定)。*

## 設定

`docker compose` は同ディレクトリの `.env` または環境変数を読む。

| 変数 | 既定 | 説明 |
|---|---|---|
| `ROS_DOMAIN_ID` | `0` | **ホストと一致必須**。ずれるとフリートが見えない |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | **ホストと一致必須** |
| `USE_SIM_TIME` | `false` | 実機運用なら `false`(既定)、シミュレーションなら `true` |
| `RMF_API_SERVER_HOST` | `127.0.0.1` | 別マシンのブラウザから開くなら `0.0.0.0` |
| `RMF_API_SERVER_PUBLIC_URL` | `http://localhost:8000` | 上記を変えた場合は実IPに合わせる |
| `RMF_WEB_IMAGE_TAG` | `jazzy-nightly` | api-server イメージのタグ |
| `DASHBOARD_PORT` | `3000` | ダッシュボードの待受ポート |
| `DASHBOARD_ZOOM` | (`main.tsx` の既定 `2000`) | マップの初期ズーム |
| `DASHBOARD_ROBOT_ZOOM` | (`main.tsx` の既定 `4000`) | ロボット注目時のズーム |
| `DASHBOARD_API_SERVER_URL` | (`main.tsx` の既定 `http://localhost:8000`) | ブラウザから見た api-server の URL(ビルド時に埋め込み) |
| `DASHBOARD_TRAJECTORY_SERVER_URL` | (`main.tsx` の既定 `http://localhost:8006`) | 同じくトラジェクトリサーバの URL |
| `DASHBOARD_ROBOT_RADIUS` などマーカー実寸5変数 | (空 = upstream の既定サイズ) | マーカーの実寸(m)。「床面図がまったく見えない」の節を参照 |
| `RMF_API_SERVER_PORT` | `8000` | api-server の待受ポート |
| `RMF_API_SERVER_LOG_LEVEL` | `INFO` | api-server のログレベル |
| `TZ` | `Asia/Tokyo` | スケジューラのタイムゾーン(システム・UIと揃える) |

シミュレーションで使う例:

```bash
USE_SIM_TIME=true docker compose up -d
```

ズームはビルド時に埋め込まれる値のため、変更後は再ビルドが必要:

```bash
DASHBOARD_ZOOM=12 docker compose build dashboard && docker compose up -d
```

## toio 向けにデモ設定から変えている点

`docker/dashboard/main.tsx` が rmf-web の `examples/demo/main.tsx` を置き換える。

| 項目 | upstream デモ | toio |
|---|---|---|
| `defaultZoom` | `6`(6 px/m) | `2000`(2000 px/m)。A3マットは 0.42 × 0.30 m しかないため |
| `defaultRobotZoom` | `20` | `4000` |
| `allowedTasks` | patrol / delivery / compose-clean / custom_compose | **patrol / delivery**。delivery フォームの pickup/dropoff 選択肢はビルディングマップの `pickup_dispenser` / `dropoff_ingestor` vertex params(toio_rmf_maps の `patrol_*` 頂点に設定)から作られる。handler には mockワークセル名が自動で入る。sku / quantity はフォーム必須だが mockワークセルは内容を見ないので任意の値でよい |
| ドア・エレベータのアプリ | あり | 削除。`toio_rmf.launch.py` は door / lift supervisor を起動しない |

## 確認項目

- [ ] Map タブにマットの床面図と nav グラフが表示される
- [ ] Robots タブに `toio1` / `toio2` がフリート `toio` として並び、位置が更新される
- [ ] Tasks タブから patrol を投入し、完走してチャージャーに帰還する
- [ ] CLI(`dispatch_patrol`)で投入したタスクもダッシュボードに現れる
- [ ] バッテリ残量が表示される

## コンテナを使わない構成

macOS など `network_mode: host` が本来の意味で使えない環境向け。
api-server はただの Python アプリ、ダッシュボードはビルド済みの静的ファイルなので、
**両方ともホストで直接動かせる**。ホストの ROS 2 環境をそのまま使うため、
DDS の到達性・ポート衝突・amd64 エミュレーションのすべてが問題にならない。

### api-server

ROS 2 環境の Python に venv を重ねる。`--system-site-packages` により
`rclpy` や `rmf_*_msgs` はホスト側のものがそのまま見える。

```bash
curl -fsSL https://github.com/open-rmf/rmf-web/archive/c91f0d42.tar.gz | tar zx

python3 -m venv --system-site-packages ~/rmfweb_venv
~/rmfweb_venv/bin/pip install rmf-web-c91f0d42/packages/api-server
```

依存は FastAPI / uvicorn / tortoise-orm / pyjwt などの純 Python パッケージのみで、
ネイティブビルドは発生しない。設定は `docker/api-server/toio_config.py` を参考に
`db_url` と `cache_directory` を書き込み可能な場所へ向けたものを用意する。

```bash
RMF_API_SERVER_CONFIG=<config.py> ~/rmfweb_venv/bin/python -m api_server
```

ROS 2 環境を有効にしたシェルで起動すること(このワークスペースなら
`pixi run ~/rmfweb_venv/bin/python -m api_server`)。

### ダッシュボード

配信対象は `dist` の静的ファイル 3.5MB だけなので、ビルド済みイメージから
取り出せば任意の HTTP サーバで配信できる。

```bash
docker create --name tmp toio-rmf-dashboard:latest
docker cp tmp:/opt/dashboard ./dashboard-dist && docker rm tmp
npx serve -s dashboard-dist -l 3000
```

**SPA フォールバックのある配信を使うこと。** `python3 -m http.server` では
`/robots` や `/tasks` を直接開いた場合とリロードで 404 になる(コンテナの
ENTRYPOINT が `serve -sn` なのはこのため)。`serve` を使えない場合は
`SimpleHTTPRequestHandler` で存在しないパスを `index.html` に振り替える。

イメージのビルドだけは amd64 が要る。Linux(amd64)機で一度ビルドして
`dist` を持ってくれば、macOS 側に Docker は要らない。

### 動作確認済みの範囲

macOS(pixi + RoboStack jazzy)+ 実機 toio で確認 (2026-08-10)。
compose 構成では失敗する以下が、ネイティブでは動く:

| 機能 | compose (macOS) | ネイティブ |
|---|:-:|:-:|
| fleet 状態(WebSocket 経由) | OK | OK |
| `GET /building_map` | 404 | **OK** |
| `POST /tasks/dispatch_task` | `rmf service timed out` | **OK**(入札・落札まで完走) |

## トラブルシュート

**フリートやロボットが表示されない**

api-server がホストの ROS 2 グラフに参加できていない可能性が高い。
`ROS_DOMAIN_ID` と `RMW_IMPLEMENTATION` がホストと一致しているか確認する。

```bash
docker compose logs api-server
docker compose exec api-server env | grep -E 'ROS_DOMAIN_ID|RMW_IMPLEMENTATION'
```

**ホスト側の ROS 2 ノードが一切起動しなくなった(macOS)**

Docker Desktop for Mac でコンテナを `network_mode: host` かつホストと同じ
`ROS_DOMAIN_ID` で起動すると、`com.docker` が macOS 側で **UDP 7400 / 7401 /
7410 / 7411**(ドメイン0の DDS discovery ポート)を占有し、ホストの participant
が作れなくなる。ブリッジも RMF も次のエラーで即死し、原因が推測できない:

```
rclpy._rclpy_pybind11.RCLError: error creating node: error not set
```

`docker compose down` すれば即座に回復する。占有の確認:

```bash
lsof -nP -iUDP | grep -E ':74[01][01]'
```

コンテナの `ROS_DOMAIN_ID` を別値にすればホストは回復し、fleet state の表示も
できる(fleet adapter からの WebSocket 経由のため DDS 不要)。ただし**タスク投入は
できない** — api-server は ROS 2 トピック `/task_api_requests` /
`/task_api_responses` 経由で投げるため、`rmf service timed out` (HTTP 500) になる。
macOS で監視だけしたい場合の妥協案であって、本来の構成ではない。

**タスクが実行されない / 時刻がおかしい**

実機運用時は `USE_SIM_TIME=false`(既定)、シミュレーション実行時は
`USE_SIM_TIME=true` にする。ここがずれると api-server が `/clock` を待ち続けたり、
開始時刻が過去や未来にずれたりする。

**ダッシュボードが白画面になる**

`RMF_WEB_REF` を `jazzy` にしてビルドすると、画面が真っ白になり
コンソールに**メッセージのない `Error`** だけが出る。**現在の Dockerfile は
回避のため既定を `c91f0d42` に固定してあるので、既定のままビルドすれば起きない**。
症状としては react-router の invariant で、
`<Routes>` が `<Router>` のコンテキスト外だと判定されている
(本番ビルドはメッセージが削られるため内容が出ない)。

**upstream 側の問題**で、本リポジトリの `main.tsx` は関係ない。根拠:

- upstream 公式イメージ `ghcr.io/open-rmf/rmf-web/demo-dashboard:jazzy-nightly`
  でも**同じ難読化位置**(`Lo` at 240:66679 / `j8` at 240:80093)で同じエラーが出る
- 一方 `demo-dashboard:latest` は正常に描画し `/login` へ遷移する
- 本リポジトリの `main.tsx` と upstream の `examples/demo/main.tsx` の差分は
  zoom 値・URL・タスク種別・アプリ一覧だけで、レンダー構造は同一

既定の `c91f0d42` は `Update deps (#1083)` (2026-05-08) の直前のリビジョンで、
明示的に指定してビルドする場合は:

```bash
docker build --platform linux/amd64 --build-arg RMF_WEB_REF=c91f0d42 \
  -t toio-rmf-dashboard:latest ./dashboard
```

macOS + 実機 toio で確認 (2026-08-10)。`jazzy` は `index-DJmLw7mG.js` で白画面、
`c91f0d42` は `index-CyV80R56.js` で正常描画し、Robots タブに実機のバッテリー
30% / CHARGING が表示された。upstream が修正されたら既定を `jazzy` に戻してよい。

**マップが点にしか見えない、または見切れる**

`DASHBOARD_ZOOM` を調整して再ビルドする。ズームは「1メートルあたりのピクセル数」(線形)で、
値を大きくするほど拡大される。

**床面図がまったく見えない場合はズームではなくマーカーのサイズが原因**。
upstream の rmf-dashboard-framework は描画サイズを数十m級の建物向けに
ハードコードしており、そのままでは toio のマット(A4 で 0.297 x 0.210 m)の
床面図を完全に覆い隠す:

| 描画物 | upstream の実サイズ | 出典 |
|---|---|---|
| waypoint(立方体) | 一辺 **0.65 m**(マット幅の2.2倍) | `shape-three-rendering.tsx` の `boxGeometry [1.3,1.3,1.3]` × `scale 0.5` |
| waypoint(円) | 半径 **0.3 m** | 同 `Circle args={[0.3, 64]}` |
| waypoint の高さ | z = **4 m** | 同 `HEIGHT = 8` |
| ロボット | `DEFAULT_ROBOT_SCALE = 0.003` | `map.tsx`(フリート設定で上書き可) |

この表のサイズは(`DEFAULT_ROBOT_SCALE` を除き)、本リポジトリの
`patches/marker-sizes.patch` によってビルド時の `VITE_TOIO_*` 変数で変えられる。
`.env` で `DASHBOARD_ROBOT_RADIUS` / `DASHBOARD_WAYPOINT_SIZE` /
`DASHBOARD_WAYPOINT_RADIUS` / `DASHBOARD_MARKER_HEIGHT` / `DASHBOARD_LABEL_SIZE`
に実寸(m)を設定して再ビルドすると反映される(推奨値は `.env.example` の
コメントを参照。空のままだと upstream の既定サイズになる)。compose を使わず
`docker build` で直接ビルドした場合は、Dockerfile の ARG 既定として toio の
実寸(半径 0.016 m など)が入る。
設定を変えずに確認だけしたいときは、**レイヤボタンから `Waypoints` や `Robots` の
チェックを外しても床面図が見える**(A4 マットで確認済み 2026-08-10)。

なお toio の床面図 PNG は 60x40px で、黒いのは外周1pxの枠だけ(内側は完全な白)。
そのため、覆い隠すものを消しても見えるのは細い枠線だけになる。見栄えを良くするには
`toio_rmf_maps` 側で床面図に中身を持たせる必要がある。

**arm64 のマシンでビルドしたい**

ベースイメージが amd64 のみのため、エミュレーションになる。

```bash
docker build --platform linux/amd64 -t toio-rmf-dashboard:latest ./dashboard
```

非常に時間がかかるので、実運用の Ubuntu(amd64)機でビルドすることを勧める。

Apple Silicon の Docker Desktop では、**Rosetta を有効にしないとビルドが落ちる**。
既定は qemu で、`pnpm install` 中に `@swc/core` の postinstall が
`qemu: uncaught target signal 11 (Segmentation fault)` (exit code 139) になる。

Settings → General → 「Use Rosetta for x86_64/amd64 emulation」を有効にして
Docker Desktop を再起動すると通るようになり、速度も大きく改善する。

なお `docker build ... | tail` のようにパイプすると終了コードが `tail` のものに
なり、この失敗を成功と読み違えるので注意。

**patrol 以外のタスクを投入したい**

`docker/dashboard/main.tsx` の `allowedTasks` に追加して再ビルドする。ただし
フリート設定(`toio_fleet_config_<mat>.yaml`)の `task_capabilities` で
有効になっていないタスクは落札されない(現在有効なのは loop と delivery。
delivery にはRMF本体へのパッチが必要 — [docs/TASKS.md](TASKS.md) 参照)。
delivery のフォームが要求する place→handler 対応はビルディングマップの
vertex params 由来なので、選択肢に出したい waypoint は toio_rmf_maps 側で
`pickup_dispenser` / `dropoff_ingestor` を持っている必要がある。

## 関連ドキュメント

- [README](../README.md) — 起動方法と launch 引数
- [docs/TASKS.md](TASKS.md) — サンプルタスクの図解
- [docs/SETUP.md](SETUP.md) — 環境構築手順
