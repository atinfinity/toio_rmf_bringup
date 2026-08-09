"""rmf-web api-server の設定(toio 環境向け)。

upstream の ``sqlite_local_config.py`` は ``use_sim_time`` を true に固定して
いるため、実機運用(``use_sim_time:=false``)でそのまま使うと RMF ノード群と
時刻がずれる。ここでは環境変数で切り替えられるようにしている。

コンテナ内では ``/ws/toio_config.py`` にマウントし、環境変数
``RMF_API_SERVER_CONFIG`` から参照させる(compose.yaml 参照)。
"""

import os
from os.path import dirname

from api_server.default_config import config


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if not value:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


here = dirname(__file__)

# api-server イメージの ENTRYPOINT が WORKDIR(/ws)に run/cache を作るため、
# 既定はこの設定ファイルと同じ場所を基準にする
run_dir = os.environ.get('RMF_API_SERVER_RUN_DIR') or f'{here}/run'

use_sim_time = _flag('USE_SIM_TIME', True)

config.update(
    {
        # 既定は 127.0.0.1。別マシンのブラウザから開く場合は 0.0.0.0 にする
        'host': os.environ.get('RMF_API_SERVER_HOST') or '127.0.0.1',
        'port': int(os.environ.get('RMF_API_SERVER_PORT') or 8000),
        # ブラウザから見えるURI。host を 0.0.0.0 にした場合はここも実IPにする
        'public_url': (
            os.environ.get('RMF_API_SERVER_PUBLIC_URL') or 'http://localhost:8000'
        ),
        'db_url': f'sqlite://{run_dir}/db.sqlite3',
        'cache_directory': f'{run_dir}/cache',
        # ROS ノードに渡す引数("--ros-args" は api_server 側で前置される)。
        # シミュレーション時は Gazebo の /clock に追従させる必要がある
        'ros_args': [
            '-p',
            f"use_sim_time:={'true' if use_sim_time else 'false'}",
        ],
        'log_level': os.environ.get('RMF_API_SERVER_LOG_LEVEL') or 'INFO',
        # スケジューラはシステムおよびUIと同じタイムゾーンである必要がある
        'timezone': os.environ.get('TZ') or 'Asia/Tokyo',
    }
)
