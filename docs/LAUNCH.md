# 起動方法とタスク投入

環境構築が済んでいる前提で書く。未構築なら [docs/SETUP.md](SETUP.md) を先に読むこと。

## 起動

デフォルトは**実機運用**(`use_sim_time:=false` / `run_sim:=false`)。
シミュレーションで動かす場合は両方を明示的に `true` にする。

### 実機

起動は2段階。**実機ブリッジを先に起動すること**。nav2 の costmap はブリッジ由来の
TFを待つため、逆順で `initial_transform_timeout` を超えると、nav2 が
恒久的に起動失敗する(詳細と復旧方法は [SETUP.md](SETUP.md) の「起動(2端末)」を参照)。

```bash
# 端末1: 実機ブリッジ(BLE接続。キューブの電源を入れてから)
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_ros2 toio_multi_bringup.launch.py

# 端末2: RMFコア + フリートアダプタ + Nav2 一式
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a4
```

キューブの初期配置(チャージャー頂点への置き方)は
[SETUP.md](SETUP.md) の「キューブの初期配置」を参照。

### シミュレーション

```bash
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 run_sim:=true use_sim_time:=true
```

### 主な引数

| 引数 | デフォルト | 説明 |
|---|---|---|
| `mat` | `a3` | 使用マット(`a3` / `a4`) |
| `use_sim_time` | `false` | シミュレーション時刻を使用(シミュレーション時は `true`) |
| `run_sim` | `false` | toio_gazeboマルチシミュレーションも起動(実機運用では別途ブリッジを起動する) |
| `run_nav` | `true` | toio_navigation(Nav2)も起動 |
| `robots` | `toio1,toio2` | Nav2を立てるロボットの名前空間(カンマ区切り、toio_multi_navigationへ渡る)。Gazeboシミュレーションが出すのは固定の toio1 / toio2 |
| `use_nav_rviz` | `false` | ロボット毎のNav2 RVizを起動 |
| `rmf_headless` | `false` | RMFスケジュールビジュアライザRVizを抑止 |
| `server_uri` | `''` | rmf-web api-serverのURI(任意) |

## タスク投入例

```bash
# patrol: patrol_A → patrol_D を3周(シミュレーション時は --use_sim_time を付ける)
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 3
```

`dispatch_patrol` の引数:

| 引数 | デフォルト | 説明 |
|---|---|---|
| `-p` / `--places` | (必須) | 巡回先のwaypoint名。スペース区切りで複数指定し、並べた順に訪問する |
| `-n` / `--rounds` | `1` | `-p` の並びを何周するか |
| `-F` / `--fleet` | — | フリート名。本パッケージでは `toio` |
| `-R` / `--robot` | — | ロボット名(`toio1` / `toio2`)。`-F` と併用したときだけ有効で、入札を経ずそのロボットへ直接割り当てる(`robot_task_request`)。`-F` 単独ならそのフリート内で入札させる |
| `-st` / `--start_time` | `0` | 何秒後に開始するか |
| `--use_sim_time` | 無効 | シミュレーション時刻を使う。`use_sim_time:=true` で起動した場合は付ける |

`-pt` / `--priority` も受け付けるが、上流 `rmf_demos_tasks` 側が未実装
(`todo(YV): Fill priority after schema is added`)でリクエストに反映されない。

特定の1台だけを動かす例:

```bash
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 3 -F toio -R toio1
```

delivery タスクも投入できる(pickup / dropoff の荷役要求には launch が起動する
mockワークセル `toio_dispenser` / `toio_ingestor` が応答する)。

各タスクの中身(走行経路・投入の流れ・delivery / go_to_place / ChargeBattery /
キャンセル)は [docs/TASKS.md](TASKS.md) に図で解説している。

ブラウザからタスクを投入・監視したい場合は、rmf-web(api-server + ダッシュボード)を
コンテナで起動できる(任意)。手順は [docs/DASHBOARD.md](DASHBOARD.md) 参照。

navグラフの頂点名(`patrol_A` など)とマットごとの注意点は
[docs/ARCHITECTURE.md](ARCHITECTURE.md) の「navグラフ頂点」を参照。

## 関連ドキュメント

- [README](../README.md) — 概要とクイックスタート
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — 構成とパッケージ関係
- [docs/TASKS.md](TASKS.md) — サンプルタスクの図解
- [docs/DASHBOARD.md](DASHBOARD.md) — rmf-web ダッシュボード
