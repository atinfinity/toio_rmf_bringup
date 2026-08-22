# toio_rmf_bringup

[![colcon-test](https://github.com/atinfinity/toio_rmf_bringup/actions/workflows/colcon-test.yml/badge.svg)](https://github.com/atinfinity/toio_rmf_bringup/actions/workflows/colcon-test.yml)

Open-RMFコア・toio用フリートアダプタ・Gazeboシミュレーション・Nav2を
1コマンドで一括起動するパッケージ。対応ディストリは **ROS 2 Jazzy(Ubuntu 24.04)のみ**。

![パッケージ構成と接続関係](docs/images/package_relations.svg)

## クイックスタート

環境構築がまだなら [docs/SETUP.md](docs/SETUP.md) を参照。
`scripts/setup_environment.sh` でapt導入からビルドまで自動化できる。

シミュレーションで動かす:

```bash
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 run_sim:=true use_sim_time:=true
```

別の端末からタスクを投入する:

```bash
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 3 --use_sim_time
```

実機で動かす場合は実機ブリッジを先に起動する必要がある。手順と launch 引数の一覧は
[docs/LAUNCH.md](docs/LAUNCH.md) を参照。

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | 環境構築手順・ハマりどころ・実機検証の手順 |
| [docs/LAUNCH.md](docs/LAUNCH.md) | 実機/シミュレーションの起動方法・launch 引数・タスク投入例 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 構成図の読み方・関連パッケージ一覧・navグラフ頂点とマットごとの注意 |
| [docs/TASKS.md](docs/TASKS.md) | patrol / delivery などサンプルタスクの図解 |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | rmf-web ダッシュボードの起動(任意) |

**Open-RMFのフリート処理を段階的に学びたい方**(ROS 2中級者向け): toio_gazebo
シミュレーションで入札・交通調停・充電までを手を動かして学ぶチュートリアルを
別リポジトリ [toio_rmf_tutorial](https://github.com/atinfinity/toio_rmf_tutorial)
に用意している。
