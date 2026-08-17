# 章9: 可視化とダッシュボード

← [前章: フリートアクション](08_fleet_action.md) | [目次](README.md) | 次章: [実機へ →](10_real_robot.md)

## 狙い

- ここまで断片的に使ってきた **RViz** の見方を整理する(何がどの層の情報か)
- ブラウザからタスク投入・監視ができる **rmf-webダッシュボード**を立てる
  (任意 ── CLIとRVizだけでも運用できる)
- sim編の総仕上げとして、「投入 → 走行 → 完了」をGUIで一望する

## RVizで何が見えているか

`toio_rmf.launch.py` は既定でRVizを起動する。表示物を[章1](01_architecture.md)の
三層に対応づけて読むと、ただの絵が**内部状態の可視化**になる:

| RVizの表示 | 対応する層・情報 |
|---|---|
| navグラフ(頂点とレーン) | RMFの地図。タスクで指定する `patrol_A` 等の正体([章3](03_patrol.md)) |
| 経路帯(schedule) | 大域交通調停の予約。誰がどのレーンをいつ通るか([章5](05_traffic.md)) |
| ロボットの球(fleet state) | フリートアダプタの自己申告。`/fleet_states` の位置 |
| 床面図(floorplan) | building_map_server が配る建物図 |

> toioのマットは数cm〜数十cm。RMFの可視化は数十m級の建物向けに作られている
> ため、[章0](00_setup.md)で触れたパッチを当てておかないとマーカーがマットを
> 覆い隠す。パッチの背景は [docs/SETUP.md](../SETUP.md) に詳しい。

**やってみる**: [章5](05_traffic.md)の2台交差タスクをもう一度投げ、RVizで
経路帯が2本引かれ、競合区間で片方が待つ/迂回する様子を観察する。CLIログで
読んでいた交通調停が、絵として一望できる。

## rmf-webダッシュボード(任意)

ブラウザからタスクを投げ、フリートを監視するGUI。ROS 2スタックはホストで
そのまま動かし、rmf-webだけをコンテナ化する構成。**使わなくても本パッケージ
の動作には影響しない**ので、GUIを試したい人向け。

構築とトラブルシュートの全ては [docs/DASHBOARD.md](../DASHBOARD.md) に
あるので、ここでは最短の流れだけ示す。

### 1. ダッシュボードイメージをビルド(初回のみ)

```bash
cd ~/dev_ws/src/toio_rmf_bringup/docker
docker compose build dashboard
```

### 2. コンテナ起動(シミュレーションなので USE_SIM_TIME=true)

```bash
USE_SIM_TIME=true docker compose up -d
docker compose logs -f api-server   # 起動確認
```

### 3. ROS 2スタックを server_uri 付きで起動

端末Aを、ダッシュボードのapi-serverに繋ぐ形で起動し直す:

```bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py \
  mat:=a3 run_sim:=true use_sim_time:=true \
  server_uri:=ws://localhost:8000/_internal
```

### 4. ブラウザで開く

<http://localhost:3000>

- **Map** タブ … マットと2台のキューブ
- **Robots** タブ … `toio1` / `toio2` がフリート `toio` として並び、位置と
  バッテリが更新される([章6](06_battery_charge.md)で見た値がGUIに出る)
- **Tasks** タブ … patrol / delivery をフォームから投入できる

**やってみる**: Tasksタブから patrol を投入し、CLI(`dispatch_patrol`)で
投げたときと**同じタスクがGUIにも現れる**ことを確認する。CLIとGUIは同じ
RMFコアに繋がっている ── 入口が違うだけ。

> ダッシュボードには既知の注意点(白画面・マーカーがマットを覆う・macOSでの
> ネットワーク制約など)がいくつかある。詰まったら
> [docs/DASHBOARD.md のトラブルシュート](../DASHBOARD.md)を先に見ること。

## 理解する

- **RVizは開発者の観察窓、ダッシュボードは運用者の操作卓**。RVizは内部状態
  (予約・TF・navグラフ)を細かく見るのに向き、rmf-webは「タスクを投げて
  結果を見る」運用に向く。目的で使い分ける。
- どちらも**RMFコアの状態を映しているだけ**で、コアの動作を変えるものでは
  ない。GUIから投げたpatrolも、CLIから投げたpatrolも、入札→交通調停→充電
  という同じ処理を通る(章4〜6)。可視化は理解を助けるが、本質は下の層に
  ある、という視点を保つ。

## 確認課題

1. RVizで2台交差タスクの経路帯を観察し、[章5](05_traffic.md)でログから読んだ
   「待ち・迂回」が絵として一致することを確認する。
2. (ダッシュボードを立てた人)Tasksタブから patrol を投入し、Robotsタブで
   バッテリと位置が更新されるのを見る。CLI投入のタスクもTasks一覧に出るか。
3. 同じ1本のpatrolを、RVizとダッシュボードの**両方で同時に**眺め、片方が
   絵、もう片方が表として同じ出来事を映していることを体感する。

これでシミュレーション編は完走。最後の章で、ここまで学んだことを**実機の
toioキューブ**へ持っていく ── 何が変わり、何が変わらないかを見る。

← [前章: フリートアクション](08_fleet_action.md) | [目次](README.md) | 次章: [実機へ →](10_real_robot.md)
