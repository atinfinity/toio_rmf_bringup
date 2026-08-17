# 章6: バッテリと自動充電(ChargeBattery)

← [前章: 交通調停](05_traffic.md) | [目次](README.md) | 次章: [搬送とワークセル →](07_delivery.md)

## 狙い

- RMFがロボットのバッテリを見張り、**尽きる前に勝手に充電へ帰す**仕組みを知る
- 明示的に投げるタスクではない **ChargeBattery** が、どんな条件で自動計画
  されるかをフリート設定から理解する
- 実行中タスクを**キャンセル**する操作を覚える(充電・帰還と絡む)

入札(章4)・交通調停(章5)に続く、フリートの**自己管理**の層。

## ChargeBatteryは「投げない」タスク

これまでのタスク(go_to_place / patrol)はCLIから投げた。ChargeBatteryは違い、
**RMFが「このままだとバッテリが足りない」と判断したときに自動で計画する**。
運用者が忘れていても、ロボットが自分で充電に帰る ── これがフリートを
長時間ほったらかせる理由。

判断はフリート設定 `toio_fleet_config_<mat>.yaml` の値で決まる:

| パラメータ | 値 | 意味 |
|---|---|---|
| `recharge_threshold` | `0.2` | 残量がこれを**下回る見込み**になると充電を計画 |
| `recharge_soc` | `1.0` | 充電の目標残量(満充電) |
| `account_for_battery_drain` | `true` | 見積もり時にバッテリ消費を織り込む |
| `finishing_request` | `"charge"` | タスク完了後もチャージャーへ帰す |

`account_for_battery_drain: true` が効いているので、RMFは**入札の段階から**
「このタスクを最後までやったらバッテリはいくつになる?」を計算している。
足りなくなる見込みなら、先に充電を挟む。

## 状態遷移で捉える

```
        タスク受注              残量が閾値を下回る見込み
  ┌──────────────┐          ┌───────────────────┐
  ▼              │          ▼                   │
待機(charger) ─→ 実行中 ─────────────→ 充電帰還(ChargeBattery自動計画)
  ▲              │  完了時 finishing_request     │
  │              └──────── charge で帰還 ────────┘
  └───────────── 自機の charger へ帰り充電待機 ←──┘
```

図の詳細版は [docs/TASKS.md の ChargeBattery](../TASKS.md) にある。

## 動かす・観察する

### 1. バッテリの現在値を見る

シミュレーションでもRMFはバッテリ残量を**推定して**持っている(フリート設定の
バッテリ消費モデルから計算)。まず現状を見る:

```bash
ros2 topic echo /fleet_states --once
```

各ロボットの `battery_percent`(0.0〜1.0)が入っている。充電待機中は満充電
付近のはず。

> 実機ではこの値が推定ではなく、キューブ実測(`/toioN/toio/battery_state` の
> `percentage`、10%刻みの離散値)由来になる。sim/realの差は
> [章10](10_real_robot.md)で扱う。

### 2. 長いタスクで充電計画を誘発する

閾値を割り込ませるには、**バッテリを大きく消費する見込み**のタスクを与える。
長周回のpatrolが手軽:

```bash
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_B patrol_C patrol_D -n 10 --use_sim_time
```

**観察**: 周回を重ねるうち、RMFが残量の見込みが `recharge_threshold` を割ると
判断すると、patrolの合間や完了後に **ChargeBattery** を自動で挟み、自機の
チャージャーへ帰す。`rmf_task_dispatcher` のログに、投げていないはずの
充電タスクが現れる。

> 消費モデルの値によっては10周でも閾値に届かないことがある。その場合は
> 周回数を増やすか、`toio_fleet_config_<mat>.yaml` の `recharge_threshold` を
> 一時的に大きく(例:0.9)して**わざと発火させて**観察するとよい。設定を
> 変えたら端末Aを起動し直す。学習のための誘発なので、確認後は元に戻す。

### 3. 完了後の自動帰還を見る(finishing_request)

短いpatrolでも、**完了後にチャージャーへ帰る**のは `finishing_request: "charge"`
の働き。章3で見た「勝手に帰る」挙動の正体がこれ。ChargeBatteryの「途中で
帰る」と、finishing_requestの「終わったら帰る」は別トリガだが、どちらも
「充電待機へ戻す」点で連続している。

## キャンセルと帰還

実行中のタスクは途中で取り消せる。取り消したロボットは `finishing_request` に
従ってチャージャーへ戻る:

```bash
ros2 run rmf_demos_tasks cancel_task -id <task_id>
```

- `task_id` は投入時のCLI出力、または `rmf_task_dispatcher` のログに出る
- **`cancel_task` は `--use_sim_time` を受け付けない**(`-id` のみ)。
  このチュートリアルで唯一 `--use_sim_time` を付けないコマンド。

**やってみる**: 長いpatrolを投げ、途中で `cancel_task -id <task_id>` する。
ロボットが巡回をやめてチャージャーへ帰るのを確認する。

## 理解する

- **バッテリ管理はフリートの自律性の要**。入札で「誰が」、交通調停で「どう
  道を分けるか」を見てきたが、ChargeBatteryは**「いつ休むか」を自分で決める**
  層。この3つが揃うと、運用者は個々のロボットの世話をしなくてよくなる。
- **見積もりにバッテリが入る**ので、章4の入札と繋がっている。残量の少ない
  ロボットは「やったら足りなくなる」と見積もられ、入札で不利になったり、
  受注前に充電を挟んだりする。**入札・充電・タスク実行は独立でなく連動**。
- **finishing_request と ChargeBattery は別物**。前者は「タスク完了後の
  片付けポリシー」、後者は「実行中に残量が危ういときの割り込み」。混同
  しやすいが、トリガが違う。

## 確認課題

1. `/fleet_states` の `battery_percent` を echo し続けながら長いpatrolを投げ、
   残量が下がっていく様子と、閾値付近でChargeBatteryが挟まる瞬間を捉える。
2. `recharge_threshold` を一時的に0.9へ上げて発火を確実にし、充電帰還を観察
   してから元に戻す。**設定値ひとつでフリートの「働き者度」が変わる**ことを
   体感する。
3. 実行中タスクを `cancel_task` で取り消し、ロボットがチャージャーへ戻る
   ことを確認する。キャンセルと finishing_request の関係を説明できるか。

自己管理まで見たら、次は「移動」以外のタスク ── **荷役(delivery)**へ。
ロボットだけでなく**ワークセル**という別の登場人物が出てくる。

← [前章: 交通調停](05_traffic.md) | [目次](README.md) | 次章: [搬送とワークセル →](07_delivery.md)
